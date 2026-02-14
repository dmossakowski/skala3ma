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

import os
import logging
from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, session, request, send_file
from werkzeug.utils import secure_filename

import competitionsEngine
import skala_db

# Import the admin_required decorator and session recreation from skala_api
from skala_api import admin_required, recreate_session_from_jwt

# Get data directory from environment
DATA_DIRECTORY = os.getenv('DATA_DIRECTORY')
if DATA_DIRECTORY is None:
    DATA_DIRECTORY = os.getcwd()

COMPETITIONS_DB = DATA_DIRECTORY + "/db/competitions.sqlite"
UPLOAD_FOLDER = os.path.join(DATA_DIRECTORY, 'uploads')
ALLOWED_DB_EXTENSIONS = {'sqlite', 'db', 'sqlite3'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}

# Create admin blueprint with /api1/admin prefix
skala_admin_api = Blueprint('skala_admin', __name__, url_prefix='/api1/admin')


@skala_admin_api.before_request
def before_admin_request():
    """Ensure session is recreated from JWT before each admin request."""
    recreate_session_from_jwt()


def allowed_file(filename):
    """Check if file has allowed extension for database files."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_DB_EXTENSIONS


def allowed_image(filename):
    """Check if file has allowed extension for image files."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


# ============= Database Management Endpoints =============

@skala_admin_api.route('/database/download', methods=['GET'])
@admin_required
def download_database():
    """Download the SQLite database file.
    
    Returns the competitions.sqlite database as a downloadable file.
    Requires admin permissions.
    """
    try:
        if not os.path.exists(COMPETITIONS_DB):
            return jsonify({
                'success': False,
                'error': 'database_not_found',
                'message': 'Database file does not exist'
            }), 404
        
        # Get file stats for metadata
        file_stats = os.stat(COMPETITIONS_DB)
        file_size = file_stats.st_size
        modified_time = datetime.fromtimestamp(file_stats.st_mtime).isoformat()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        download_name = f'skala3ma_competitions_{timestamp}.sqlite'
        
        logging.info(f"Admin {session.get('email')} downloading database: {download_name} ({file_size} bytes)")
        
        return send_file(
            COMPETITIONS_DB,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/x-sqlite3'
        )
    
    except Exception as e:
        logging.error(f"Error downloading database: {e}")
        return jsonify({
            'success': False,
            'error': 'download_failed',
            'message': str(e)
        }), 500


@skala_admin_api.route('/database/upload', methods=['POST'])
@admin_required
def upload_database():
    """Upload and replace the SQLite database file.
    
    Accepts a multipart/form-data upload with 'file' field.
    Creates a backup of the existing database before replacing.
    Requires admin permissions.
    
    Form data:
      - file: SQLite database file
      - create_backup: (optional) 'true' to create backup (default: true)
    """
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'no_file',
                'message': 'No file provided in request'
            }), 400
        
        file = request.files['file']
        
        # Check if file was selected
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'empty_filename',
                'message': 'No file selected'
            }), 400
        
        # Validate file extension
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'invalid_file_type',
                'message': f'File must have one of these extensions: {", ".join(ALLOWED_DB_EXTENSIONS)}'
            }), 400
        
        # Get backup preference (default to true)
        create_backup = request.form.get('create_backup', 'true').lower() != 'false'
        
        # Create backup of existing database if requested
        backup_path = None
        if create_backup and os.path.exists(COMPETITIONS_DB):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'competitions_backup_{timestamp}.sqlite'
            backup_path = os.path.join(DATA_DIRECTORY, 'db', backup_filename)
            
            try:
                import shutil
                shutil.copy2(COMPETITIONS_DB, backup_path)
                logging.info(f"Created database backup: {backup_path}")
            except Exception as backup_error:
                logging.error(f"Failed to create backup: {backup_error}")
                return jsonify({
                    'success': False,
                    'error': 'backup_failed',
                    'message': f'Failed to create backup: {str(backup_error)}'
                }), 500
        
        # Save uploaded file
        try:
            file.save(COMPETITIONS_DB)
            file_size = os.path.getsize(COMPETITIONS_DB)
            
            logging.info(f"Admin {session.get('email')} uploaded new database: {file.filename} ({file_size} bytes)")
            
            # Try to verify it's a valid SQLite database
            try:
                import sqlite3
                conn = sqlite3.connect(COMPETITIONS_DB)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                conn.close()
                
                return jsonify({
                    'success': True,
                    'message': 'Database uploaded successfully',
                    'backup_created': backup_path is not None,
                    'backup_path': os.path.basename(backup_path) if backup_path else None,
                    'file_size': file_size,
                    'tables_found': len(tables),
                    'tables': tables
                })
            
            except sqlite3.Error as db_error:
                logging.error(f"Uploaded file is not a valid SQLite database: {db_error}")
                
                # Restore backup if validation fails
                if backup_path and os.path.exists(backup_path):
                    import shutil
                    shutil.copy2(backup_path, COMPETITIONS_DB)
                    logging.info("Restored database from backup after failed validation")
                
                return jsonify({
                    'success': False,
                    'error': 'invalid_database',
                    'message': 'Uploaded file is not a valid SQLite database',
                    'database_restored': backup_path is not None
                }), 400
        
        except Exception as save_error:
            logging.error(f"Failed to save uploaded database: {save_error}")
            return jsonify({
                'success': False,
                'error': 'save_failed',
                'message': f'Failed to save database: {str(save_error)}'
            }), 500
    
    except Exception as e:
        logging.error(f"Error uploading database: {e}")
        return jsonify({
            'success': False,
            'error': 'upload_failed',
            'message': str(e)
        }), 500


@skala_admin_api.route('/database/info', methods=['GET'])
@admin_required
def database_info():
    """Get information about the current database.
    
    Returns metadata including file size, modification time, and table list.
    Requires admin permissions.
    """
    try:
        if not os.path.exists(COMPETITIONS_DB):
            return jsonify({
                'success': False,
                'error': 'database_not_found',
                'message': 'Database file does not exist'
            }), 404
        
        # Get file stats
        file_stats = os.stat(COMPETITIONS_DB)
        file_size = file_stats.st_size
        modified_time = datetime.fromtimestamp(file_stats.st_mtime).isoformat()
        created_time = datetime.fromtimestamp(file_stats.st_ctime).isoformat()
        
        # Get database schema information
        import sqlite3
        conn = sqlite3.connect(COMPETITIONS_DB)
        cursor = conn.cursor()
        
        # Get table list
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Get row counts for each table
        table_info = {}
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                table_info[table] = {'row_count': count}
            except Exception:
                table_info[table] = {'row_count': 'unknown'}
        
        conn.close()
        
        return jsonify({
            'success': True,
            'database': {
                'path': COMPETITIONS_DB,
                'file_size': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'modified': modified_time,
                'created': created_time,
                'table_count': len(tables),
                'tables': table_info
            }
        })
    
    except Exception as e:
        logging.error(f"Error getting database info: {e}")
        return jsonify({
            'success': False,
            'error': 'info_failed',
            'message': str(e)
        }), 500


@skala_admin_api.route('/database/backups', methods=['GET'])
@admin_required
def list_backups():
    """List all available database backup files.
    
    Returns list of backup files in the database directory.
    Requires admin permissions.
    """
    try:
        db_dir = os.path.join(DATA_DIRECTORY, 'db')
        if not os.path.exists(db_dir):
            return jsonify({
                'success': True,
                'backups': []
            })
        
        # Find all backup files
        import glob
        backup_pattern = os.path.join(db_dir, 'competitions_backup_*.sqlite')
        backup_files = glob.glob(backup_pattern)
        
        backups = []
        for backup_file in backup_files:
            file_stats = os.stat(backup_file)
            backups.append({
                'filename': os.path.basename(backup_file),
                'path': backup_file,
                'size': file_stats.st_size,
                'size_mb': round(file_stats.st_size / (1024 * 1024), 2),
                'created': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
            })
        
        # Sort by creation time, newest first
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({
            'success': True,
            'backup_count': len(backups),
            'backups': backups
        })
    
    except Exception as e:
        logging.error(f"Error listing backups: {e}")
        return jsonify({
            'success': False,
            'error': 'list_failed',
            'message': str(e)
        }), 500


# ============= Image Management Endpoints =============

@skala_admin_api.route('/images/list', methods=['GET'])
@admin_required
def list_images():
    """List all uploaded images in the uploads directory.
    
    Returns list of all image files with metadata.
    Requires admin permissions.
    """
    try:
        if not os.path.exists(UPLOAD_FOLDER):
            return jsonify({
                'success': True,
                'image_count': 0,
                'images': [],
                'total_size': 0
            })
        
        images = []
        total_size = 0
        
        # Walk through uploads directory
        for root, dirs, files in os.walk(UPLOAD_FOLDER):
            for filename in files:
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, UPLOAD_FOLDER)
                
                try:
                    file_stats = os.stat(filepath)
                    file_size = file_stats.st_size
                    total_size += file_size
                    
                    images.append({
                        'filename': filename,
                        'path': rel_path,
                        'full_path': filepath,
                        'size': file_size,
                        'size_kb': round(file_size / 1024, 2),
                        'modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                        'is_image': allowed_image(filename)
                    })
                except Exception as e:
                    logging.warning(f"Error reading file {filepath}: {e}")
        
        # Sort by modification time, newest first
        images.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            'success': True,
            'image_count': len(images),
            'images': images,
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'upload_folder': UPLOAD_FOLDER
        })
    
    except Exception as e:
        logging.error(f"Error listing images: {e}")
        return jsonify({
            'success': False,
            'error': 'list_failed',
            'message': str(e)
        }), 500


@skala_admin_api.route('/images/download-all', methods=['GET'])
@admin_required
def download_all_images():
    """Download all images as a zip archive.
    
    Creates a zip file containing all images from the uploads directory.
    Requires admin permissions.
    """
    try:
        if not os.path.exists(UPLOAD_FOLDER):
            return jsonify({
                'success': False,
                'error': 'folder_not_found',
                'message': 'Uploads folder does not exist'
            }), 404
        
        import zipfile
        import io
        
        # Create zip file in memory
        memory_file = io.BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Walk through uploads directory
            for root, dirs, files in os.walk(UPLOAD_FOLDER):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    arcname = os.path.relpath(filepath, UPLOAD_FOLDER)
                    try:
                        zf.write(filepath, arcname)
                    except Exception as e:
                        logging.warning(f"Error adding {filepath} to zip: {e}")
        
        memory_file.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        download_name = f'skala3ma_images_{timestamp}.zip'
        
        logging.info(f"Admin {session.get('email')} downloading all images: {download_name}")
        
        return send_file(
            memory_file,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/zip'
        )
    
    except Exception as e:
        logging.error(f"Error downloading images: {e}")
        return jsonify({
            'success': False,
            'error': 'download_failed',
            'message': str(e)
        }), 500


@skala_admin_api.route('/images/upload-all', methods=['POST'])
@admin_required
def upload_all_images():
    """Upload a zip archive of images and extract to uploads directory.
    
    Accepts a zip file and extracts all contents to the uploads folder.
    Can optionally clear existing images before upload.
    Requires admin permissions.
    
    Form data:
      - file: Zip archive containing images
      - clear_existing: (optional) 'true' to delete all existing images first
      - create_backup: (optional) 'true' to create backup before replacing (default: true)
    """
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'no_file',
                'message': 'No file provided in request'
            }), 400
        
        file = request.files['file']
        
        # Check if file was selected
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'empty_filename',
                'message': 'No file selected'
            }), 400
        
        # Validate file is a zip
        if not file.filename.lower().endswith('.zip'):
            return jsonify({
                'success': False,
                'error': 'invalid_file_type',
                'message': 'File must be a zip archive'
            }), 400
        
        clear_existing = request.form.get('clear_existing', 'false').lower() == 'true'
        create_backup = request.form.get('create_backup', 'true').lower() != 'false'
        
        # Create backup if requested
        backup_path = None
        if create_backup and os.path.exists(UPLOAD_FOLDER):
            import shutil
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'uploads_backup_{timestamp}.zip'
            backup_path = os.path.join(DATA_DIRECTORY, backup_filename)
            
            try:
                import zipfile
                with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for root, dirs, files in os.walk(UPLOAD_FOLDER):
                        for filename in files:
                            filepath = os.path.join(root, filename)
                            arcname = os.path.relpath(filepath, UPLOAD_FOLDER)
                            zf.write(filepath, arcname)
                logging.info(f"Created images backup: {backup_path}")
            except Exception as backup_error:
                logging.error(f"Failed to create backup: {backup_error}")
                return jsonify({
                    'success': False,
                    'error': 'backup_failed',
                    'message': f'Failed to create backup: {str(backup_error)}'
                }), 500
        
        # Clear existing images if requested
        if clear_existing and os.path.exists(UPLOAD_FOLDER):
            import shutil
            try:
                shutil.rmtree(UPLOAD_FOLDER)
                os.makedirs(UPLOAD_FOLDER)
                logging.info(f"Cleared existing uploads folder")
            except Exception as clear_error:
                logging.error(f"Failed to clear uploads folder: {clear_error}")
                return jsonify({
                    'success': False,
                    'error': 'clear_failed',
                    'message': f'Failed to clear existing images: {str(clear_error)}'
                }), 500
        
        # Ensure uploads folder exists
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        
        # Extract zip file
        import zipfile
        import io
        
        try:
            zip_data = io.BytesIO(file.read())
            extracted_count = 0
            skipped_count = 0
            
            with zipfile.ZipFile(zip_data, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                for file_info in zip_ref.filelist:
                    # Skip directories and system files
                    if file_info.is_dir() or file_info.filename.startswith('__MACOSX'):
                        continue
                    
                    # Extract file
                    try:
                        zip_ref.extract(file_info, UPLOAD_FOLDER)
                        extracted_count += 1
                    except Exception as extract_error:
                        logging.warning(f"Failed to extract {file_info.filename}: {extract_error}")
                        skipped_count += 1
            
            logging.info(f"Admin {session.get('email')} uploaded images zip: {extracted_count} files extracted, {skipped_count} skipped")
            
            return jsonify({
                'success': True,
                'message': 'Images uploaded successfully',
                'extracted_count': extracted_count,
                'skipped_count': skipped_count,
                'backup_created': backup_path is not None,
                'backup_path': os.path.basename(backup_path) if backup_path else None,
                'cleared_existing': clear_existing
            })
        
        except zipfile.BadZipFile:
            return jsonify({
                'success': False,
                'error': 'invalid_zip',
                'message': 'Uploaded file is not a valid zip archive'
            }), 400
        except Exception as extract_error:
            logging.error(f"Failed to extract images: {extract_error}")
            return jsonify({
                'success': False,
                'error': 'extract_failed',
                'message': f'Failed to extract images: {str(extract_error)}'
            }), 500
    
    except Exception as e:
        logging.error(f"Error uploading images: {e}")
        return jsonify({
            'success': False,
            'error': 'upload_failed',
            'message': str(e)
        }), 500


@skala_admin_api.route('/images/info', methods=['GET'])
@admin_required
def images_info():
    """Get information about the uploads directory.
    
    Returns metadata including folder size, file count, and image count.
    Requires admin permissions.
    """
    try:
        if not os.path.exists(UPLOAD_FOLDER):
            return jsonify({
                'success': True,
                'uploads_folder': UPLOAD_FOLDER,
                'exists': False,
                'total_files': 0,
                'image_files': 0,
                'total_size': 0
            })
        
        total_files = 0
        image_files = 0
        total_size = 0
        
        for root, dirs, files in os.walk(UPLOAD_FOLDER):
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    file_stats = os.stat(filepath)
                    total_size += file_stats.st_size
                    total_files += 1
                    if allowed_image(filename):
                        image_files += 1
                except Exception:
                    pass
        
        return jsonify({
            'success': True,
            'uploads_folder': UPLOAD_FOLDER,
            'exists': True,
            'total_files': total_files,
            'image_files': image_files,
            'other_files': total_files - image_files,
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        })
    
    except Exception as e:
        logging.error(f"Error getting images info: {e}")
        return jsonify({
            'success': False,
            'error': 'info_failed',
            'message': str(e)
        }), 500


@skala_admin_api.route('/images/delete', methods=['POST'])
@admin_required
def delete_image():
    """Delete a specific image file.
    
    Accepts JSON with the relative path of the image to delete.
    Requires admin permissions.
    
    JSON body:
      - path: Relative path to the image file (from uploads folder)
    """
    try:
        data = request.get_json(silent=True) or {}
        rel_path = data.get('path')
        
        if not rel_path:
            return jsonify({
                'success': False,
                'error': 'missing_path',
                'message': 'Image path is required'
            }), 400
        
        # Construct full path
        full_path = os.path.join(UPLOAD_FOLDER, rel_path)
        
        # Security check: ensure path is within uploads folder
        full_path = os.path.abspath(full_path)
        uploads_abs = os.path.abspath(UPLOAD_FOLDER)
        if not full_path.startswith(uploads_abs):
            return jsonify({
                'success': False,
                'error': 'invalid_path',
                'message': 'Invalid file path'
            }), 400
        
        # Check if file exists
        if not os.path.exists(full_path):
            return jsonify({
                'success': False,
                'error': 'file_not_found',
                'message': 'Image file not found'
            }), 404
        
        # Delete the file
        try:
            os.remove(full_path)
            logging.info(f"Admin {session.get('email')} deleted image: {rel_path}")
            
            return jsonify({
                'success': True,
                'message': 'Image deleted successfully',
                'path': rel_path
            })
        except Exception as delete_error:
            logging.error(f"Failed to delete image {rel_path}: {delete_error}")
            return jsonify({
                'success': False,
                'error': 'delete_failed',
                'message': f'Failed to delete image: {str(delete_error)}'
            }), 500
    
    except Exception as e:
        logging.error(f"Error deleting image: {e}")
        return jsonify({
            'success': False,
            'error': 'delete_failed',
            'message': str(e)
        }), 500


# ============= Health Check =============

@skala_admin_api.route('/health', methods=['GET'])
@admin_required
def admin_health():
    """Health check endpoint for admin API.
    
    Returns basic status information.
    Requires admin permissions.
    """
    return jsonify({
        'success': True,
        'service': 'skala_admin_api',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat(),
        'admin_user': session.get('email')
    })
