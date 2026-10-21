#    Copyright (C) 2023 David Mossakowski
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Gym sector layouts, stored on the gym as:
# gym['sector_layouts'] = [
#   {"valid_from": "YYYY-MM-DD",
#    "direction": "ltr" | "rtl",   # order in which lines are numbered along the wall
#    "sectors": [{"id", "name", "height", "img_id", "thumb_id", "lines": ["1", "2"]}
#                | {"id", "type": "break", ...empty sector fields}]}
# ]
# The layout in effect on a date is the one with the latest valid_from <= that date.

import io
import os
import re
import uuid
from datetime import date

from PIL import Image, ImageOps, UnidentifiedImageError

SECTOR_LAYOUTS_KEY = 'sector_layouts'

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
PHOTO_MAX_SIZE = 1280
THUMB_MAX_SIZE = 160
MAX_NAME_LENGTH = 100
MAX_LINE_LENGTH = 20
MAX_HEIGHT_M = 100
DIRECTIONS = ('ltr', 'rtl')

# only files created by save_sector_photo may be referenced from a layout
SECTOR_IMG_ID_RE = re.compile(r'^sector_[0-9a-f]{32}(_thumb)?\.webp$')


def _parse_date(value):
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _parse_height(value):
    """Wall height in meters, or None when not set."""
    if value is None or value == '':
        return None
    try:
        height = round(float(value), 1)
    except (TypeError, ValueError):
        raise ValueError('height must be a number')
    if not 0 < height <= MAX_HEIGHT_M:
        raise ValueError('height must be between 0 and %d m' % MAX_HEIGHT_M)
    return height


def get_layouts(gym):
    if not gym:
        return []
    layouts = gym.get(SECTOR_LAYOUTS_KEY)
    return layouts if isinstance(layouts, list) else []


def get_layout_for_date(gym, on_date=None):
    """Return the layout in effect on on_date (YYYY-MM-DD, default today) or None."""
    target = _parse_date(on_date) or date.today()
    active = None
    active_from = None
    for layout in get_layouts(gym):
        valid_from = _parse_date(layout.get('valid_from'))
        if valid_from is None or valid_from > target:
            continue
        if active_from is None or valid_from > active_from:
            active, active_from = layout, valid_from
    return active


def validate_layouts(layouts):
    """Return a normalized copy of layouts sorted by valid_from; raise ValueError if invalid."""
    if not isinstance(layouts, list):
        raise ValueError('layouts must be a list')

    normalized = []
    seen_dates = set()
    for layout in layouts:
        if not isinstance(layout, dict):
            raise ValueError('each layout must be an object')
        valid_from = _parse_date(layout.get('valid_from'))
        if valid_from is None:
            raise ValueError('valid_from must be a date YYYY-MM-DD')
        if valid_from in seen_dates:
            raise ValueError('duplicate valid_from ' + valid_from.isoformat())
        seen_dates.add(valid_from)

        direction = layout.get('direction') or 'ltr'
        if direction not in DIRECTIONS:
            raise ValueError('direction must be ltr or rtl')

        sectors = layout.get('sectors')
        if not isinstance(sectors, list):
            raise ValueError('sectors must be a list')

        used_lines = set()
        norm_sectors = []
        for sector in sectors:
            if not isinstance(sector, dict):
                raise ValueError('each sector must be an object')

            sector_id = str(sector.get('id') or '')
            if not re.fullmatch(r'[0-9a-f]{32}', sector_id):
                sector_id = uuid.uuid4().hex

            # row break for the sector view; keeps the full sector shape so consumers need no special case
            if sector.get('type') == 'break':
                norm_sectors.append({'id': sector_id, 'type': 'break', 'name': '', 'height': None,
                                     'img_id': '', 'thumb_id': '', 'lines': []})
                continue

            name = str(sector.get('name') or '').strip()
            if not name or len(name) > MAX_NAME_LENGTH:
                raise ValueError('sector name is required (max %d chars)' % MAX_NAME_LENGTH)

            img_id = sector.get('img_id') or ''
            thumb_id = sector.get('thumb_id') or ''
            for value in (img_id, thumb_id):
                if value and not SECTOR_IMG_ID_RE.match(value):
                    raise ValueError('invalid sector image id')

            lines = sector.get('lines') or []
            if not isinstance(lines, list):
                raise ValueError('lines must be a list')
            norm_lines = []
            for line in lines:
                line = str(line).strip()
                if not line:
                    continue
                if len(line) > MAX_LINE_LENGTH:
                    raise ValueError('line too long: ' + line[:MAX_LINE_LENGTH])
                if line in used_lines:
                    raise ValueError('line %s is in more than one sector (%s)' % (line, valid_from.isoformat()))
                used_lines.add(line)
                norm_lines.append(line)

            norm_sectors.append({
                'id': sector_id,
                'name': name,
                'height': _parse_height(sector.get('height')),
                'img_id': img_id,
                'thumb_id': thumb_id,
                'lines': norm_lines,
            })

        normalized.append({'valid_from': valid_from.isoformat(), 'direction': direction, 'sectors': norm_sectors})

    normalized.sort(key=lambda l: l['valid_from'])
    return normalized


def referenced_image_ids(layouts):
    ids = set()
    for layout in layouts or []:
        for sector in layout.get('sectors') or []:
            for key in ('img_id', 'thumb_id'):
                if sector.get(key):
                    ids.add(sector[key])
    return ids


def delete_unreferenced_images(old_layouts, new_layouts, upload_folder):
    for img_id in referenced_image_ids(old_layouts) - referenced_image_ids(new_layouts):
        if SECTOR_IMG_ID_RE.match(img_id):
            path = os.path.join(upload_folder, img_id)
            if os.path.exists(path):
                os.remove(path)


def _to_web_mode(img):
    if img.mode in ('RGB', 'RGBA'):
        return img
    if img.mode in ('P', 'LA') or 'transparency' in img.info:
        return img.convert('RGBA')
    return img.convert('RGB')


def save_sector_photo(stream, upload_folder):
    """Resize an uploaded photo into a display copy and a thumbnail (WebP, metadata stripped).

    Returns {'img_id': ..., 'thumb_id': ...}; raises ValueError for invalid uploads.
    """
    data = stream.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError('file too large (max %d MB)' % (MAX_UPLOAD_BYTES // (1024 * 1024)))
    if not data:
        raise ValueError('empty file')

    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValueError('not a supported image')

    img = _to_web_mode(ImageOps.exif_transpose(img))

    base = 'sector_' + uuid.uuid4().hex
    img_id = base + '.webp'
    thumb_id = base + '_thumb.webp'

    photo = img.copy()
    photo.thumbnail((PHOTO_MAX_SIZE, PHOTO_MAX_SIZE), Image.LANCZOS)
    photo.save(os.path.join(upload_folder, img_id), 'WEBP', quality=80, method=6)

    thumb = img.copy()
    thumb.thumbnail((THUMB_MAX_SIZE, THUMB_MAX_SIZE), Image.LANCZOS)
    thumb.save(os.path.join(upload_folder, thumb_id), 'WEBP', quality=75, method=6)

    return {'img_id': img_id, 'thumb_id': thumb_id}
