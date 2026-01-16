
class App {
    constructor() {
        this.top_notification_label = '';
        this.top_notification_level = '';
    }

    setNotification(label, level) {
        this.top_notification_label = label;
        this.top_notification_level = level;
    }
}

// Initialize the App class
const app = new App();

// ================= JWT HANDLING =================
// Key used in localStorage for the JWT
const JWT_STORAGE_KEY = 'skala3ma_jwt';

function setJwtToken(token) {
    if (token) {
        localStorage.setItem(JWT_STORAGE_KEY, token);
    }
}

function getJwtToken() {
    return localStorage.getItem(JWT_STORAGE_KEY);
}

function clearJwtToken() {
    // Clear localStorage
    try { localStorage.removeItem(JWT_STORAGE_KEY); } catch (e) { /* ignore */ }
    // Delete cookie by setting expiry in the past
    try {
        const secure = (location.protocol === 'https:') ? '; Secure' : '';
        document.cookie = 'skala3ma_jwt=; Path=/; SameSite=Lax' + secure + '; Expires=Thu, 01 Jan 1970 00:00:00 GMT';
    } catch (e) { /* ignore */ }
}

// Decode JWT payload without verifying signature (client-side convenience only)
function decodeJwtPayload(token) {
    try {
        const payloadPart = token.split('.')[1];
        const json = atob(payloadPart.replace(/-/g, '+').replace(/_/g, '/'));
        return JSON.parse(decodeURIComponent(escape(json)));
    } catch (e) { return null; }
}

// Unified fetch wrapper that automatically adds Authorization header if token exists
async function apiFetch(url, options = {}) {
    const opts = { ...options };
    opts.headers = { 'Accept': 'application/json', ...(options.headers || {}) };
    const token = getJwtToken();
    if (token) {
        opts.headers['Authorization'] = 'Bearer ' + token;
    }
    // Default: send JSON if body is plain object
    if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)) {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(opts.body);
    }
    const response = await fetch(url, opts);
    
    return response;
}

// Convenience JSON wrapper: parses JSON (or text fallback) and throws structured error on non-OK
// Options:
//   expectJson (default true) - if false, will return text even if JSON content-type
// Error shape thrown on failure:
//   { ok:false, status, statusText, url, data, rawText }
async function apiFetchJson(url, options = {}, { expectJson = true } = {}) {
    const resp = await apiFetch(url, options);
    const ctype = resp.headers.get('content-type') || '';
    let data; let rawText = null;
    if (expectJson && ctype.includes('application/json')) {
        try { data = await resp.json(); } catch (e) { data = null; }
    } else {
        try { rawText = await resp.text(); } catch (e) { rawText = null; }
    }
    if (!resp.ok) {
        throw {
            ok: false,
            status: resp.status,
            statusText: resp.statusText,
            url,
            data,
            rawText
        };
    }
    return data !== undefined ? data : rawText;
}

// Attach to window for other inline scripts/templates
window.setJwtToken = setJwtToken;
window.getJwtToken = getJwtToken;
window.clearJwtToken = clearJwtToken;
window.apiFetch = apiFetch;
window.apiFetchJson = apiFetchJson;
window.decodeJwtPayload = decodeJwtPayload;





function getColorByBgColor(bgColor) 
{
 if (!bgColor) { return ''; }
  return (parseInt(bgColor.replace('#', ''), 16) > 0xffffff / 2) ? '#000' : '#fff';
}     



    
function getColorSVGDiv(color1, color2, colorModifier, width, height, grade=''){
    var svg = getColorSVG(color1, color2, colorModifier, grade, width, height);
    return `<div style='padding:0;margin:0;width:${width};height:${height};border:0px solid black;'>${svg}</div>`;
}

function getColorSVG(color1, color2, colorModifier, grade='', width='90px', height='40px'){    

    //console.log(colorModifier);
    var svg = '';

    // Always render a full-size background first
    widthNum = parseFloat(width); if (isNaN(widthNum)) widthNum = 200;
    heightNum = parseFloat(height); if (isNaN(heightNum)) heightNum = 100;
    let bgSvg = `<svg width="${widthNum}" height="${heightNum}" viewBox="0 0 ${widthNum} ${heightNum}" xmlns="http://www.w3.org/2000/svg">\n<rect x="0" y="0" width="${widthNum}" height="${heightNum}" style="fill: ${color1}; stroke: ${color1};"/>`;
    // Overlay marble strokes if requested
    if (colorModifier === 'marble') {
      //opposite_color = color2; //(Number(`0x1${color2.slice(1)}`) ^ 0xFFFFFF).toString(16).substr(1).toUpperCase()
      //console.log(opposite_color);
      stroke = color2; //getColorByBgColor(color)
      //console.log('Generating marble SVG with color2:', color1, color2);
      highlight = '#BBBBBB'
      if (!color2 || color2.length!==7 || color1 === color2) { 
        stroke = getColorByBgColor(color1); 
    }
      
      
    // widthNum/heightNum are set above
      var scaleX = widthNum / 222;
      var scaleY = heightNum / 222;

            
    // Directly render marble strokes scaled to desired size (no pattern)
    // Original artwork bounds: x in [65,330], y in [60,225] => width=265, height=165
    // We map these to [0,widthNum] x [0,heightNum]
    const vbX0 = 65, vbY0 = 60, vbW0 = 265, vbH0 = 165;
        let scaleX2 = widthNum / vbW0;
        let scaleY2 = heightNum / vbH0;
        const overscale = 1.3; // 5% larger than the image
        scaleX2 *= overscale;
        scaleY2 *= overscale;
        const contentW = vbW0 * scaleX2;
        const contentH = vbH0 * scaleY2;
        // Translate in original coordinate space AFTER scaling (transform order: scale then translate)
        const tx = -vbX0 + ((widthNum / scaleX2) - vbW0) / 2;
        const ty = -vbY0 + ((heightNum / scaleY2) - vbH0) / 2;
        svg6 = bgSvg + `
    <!-- Test circle to verify rendering -->
    <g transform="scale(${scaleX2}, ${scaleY2}) translate(${tx}, ${ty})">
    <path style="fill: none; stroke: ${stroke}; stroke-width: 4px; vector-effect: non-scaling-stroke; stroke-opacity: 0.8;" d="M 77.193 91.531 C 77.193 109.778 102.147 123.635 117.499 111.965 C 123.743 107.219 129.691 93.485 127.26 85.532 C 126.25 82.23 121.835 74.307 124.162 70.827 C 127.742 65.475 139.972 61.215 143.302 68.738 C 156.537 98.636 125.931 136.604 94.093 130.521 C 86.765 129.121 80.617 124.785 75.817 119.177 C 73.229 116.153 71.497 111.402 67.746 109.575"/>
    <path style="fill: none; stroke: ${stroke}; stroke-width: 3px; vector-effect: non-scaling-stroke; stroke-opacity: 0.8;" d="M 76.754 135.251 C 84.848 136.199 93.444 140.298 101.495 142.31 C 116.049 145.949 132.345 136.168 142.028 126.021 C 159.535 107.674 156.859 62.071 191.822 64.965 C 195.701 65.286 197.557 71.397 195.73 74.405 C 192.708 79.381 186.724 82.812 184.287 88.072 C 179.181 99.089 178.529 116.824 170.636 126.277 C 166.252 131.528 163.216 137.127 157.515 141.284 C 133.843 158.545 87.714 157.701 65.25 139.712"/>
    <path style="fill: none; stroke: ${stroke}; stroke-width: 2.5px; vector-effect: non-scaling-stroke; stroke-opacity: 0.7;" d="M 89.245 164.007 C 104.326 164.007 119.367 166.359 134.362 164.217 C 146.192 162.527 157.934 153.952 167.078 146.921 C 183.346 134.413 187.523 113.774 200.39 98.941 C 211.672 85.933 236.782 80.072 253.375 82.625 C 254.8 82.844 259.384 87.455 257.054 88.612 C 243.9 95.145 224.82 84.474 220.667 102.946 C 218.104 114.343 222.418 131.852 214.998 141.653 C 209.978 148.286 201.364 151.333 194.588 155.707 C 159.581 178.302 118.16 176.363 77.476 176.363"/>
    <path style="fill: none; stroke: ${stroke}; stroke-width: 3px; vector-effect: non-scaling-stroke; stroke-opacity: 0.8;" d="M 89.356 184.584 C 128.683 184.584 163.502 187.314 198.171 166.407 C 206.261 161.528 214.549 156.915 220.421 149.307 C 228.457 138.893 230.463 126.235 236.64 114.872 C 248.588 92.892 275.957 85.981 299.246 85.981 C 311.095 85.981 330.649 93.379 325.308 109.31 C 324.388 112.051 322.872 115.357 321.051 117.68 C 319.054 120.229 315.74 124.849 312.831 126.168 C 308.602 128.086 302.48 124.489 298.804 123.095 C 286.542 118.446 277.708 107.857 262.977 114.071 C 253.264 118.167 250.764 129.932 246.944 138.667 C 240.607 153.155 231.044 171.107 216.188 178.478 C 192.176 190.393 163.542 190.041 143.153 209.001 C 140.01 211.924 127.831 220.402 127.762 225.029"/>
    <path style="fill: none; stroke: ${stroke}; stroke-width: 3px; vector-effect: non-scaling-stroke; stroke-opacity: 0.6;" d="M 299.371 219.588 C 284.706 219.588 275.149 195.922 278.72 183.883 C 283.16 168.912 305.219 164.832 318.376 166.38 C 323.227 166.951 328.192 176.461 322.746 179.248 C 309.457 186.05 293.348 169.444 288.925 190.127 C 286.352 202.157 311.355 212.755 319.359 215.206 C 322.604 216.199 324.945 217.666 327.797 219.484"/>
</g>
</svg>`



   
   
   

      //return `<div style='padding: 0px; margin: 0px 0px 0px 0px; width:${width}; height:${height}; border: 0px solid ${color}; background-color: ${color}'> 
        //${svg6}  </div>`
        baseSvg = svg6;
    } else {
                baseSvg = bgSvg + `</svg>`;

  }
    // Add grade overlay scaled proportionally to passed width/height (centered) if provided
    if (grade) {
        //console.log('Adding grade overlay:', grade);
        var escaped = String(grade).replace(/[&<>"]/g, function(ch){
            return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch]);
        });
        // Parse numeric width/height (default baseline 90x40)
        var widthNum2 = widthNum; if (isNaN(widthNum2)) widthNum2 = 90;
        var heightNum2 = heightNum; if (isNaN(heightNum2)) heightNum2 = 40;
        var baseW = 90, baseH = 40;
        var scaleX = widthNum2 / baseW;
        var scaleY = heightNum2 / baseH;
        // SVG logical box (kept for existing marble artwork)
        var vbX = 100, vbY = 100, vbW = 200, vbH = 100;
        // Proportional margins (scale previous hard-coded 30/20 with width/height scales)
        var marginX = 30 * scaleX; // previously 30
        var marginY = 20 * scaleY * 0.5; // reduce a bit for better vertical usage
        // Ensure margins don't exceed half dimensions
        if (marginX > vbW * 0.4) marginX = vbW * 0.4;
        if (marginY > vbH * 0.3) marginY = vbH * 0.3;
        // Grade font sizing: fit by width (95%) for narrow, and by height (95%) for wide
        var w = widthNum; var h = heightNum;
        var shorter = Math.min(w, h);
        var longer = Math.max(w, h);
        var text = escaped;
        var charCount = 3;
        var charWidthFactor = 0.6 ; // Helvetica approx
        var fontByHeight = Math.floor(h * 0.98);
        var fontByWidth = Math.floor((w * 0.98) / Math.max(charCount * charWidthFactor, 1));
        var fontSize = Math.max(10, Math.min(fontByHeight, fontByWidth));
        var centerX = w / 2;
        var centerY = h / 2 + 2
                var txtColor = '#ffffff';
                var backdropW = Math.floor(Math.min(w * 0.95, Math.max(charCount * charWidthFactor * fontSize * 1.1, shorter * 0.6)));
            var backdropH = Math.floor(fontSize * 1.20);
        var backdropX = Math.floor(centerX - backdropW / 2);
        var backdropY = Math.floor(centerY - backdropH / 2);
                var overlay = `<defs>
    <filter id="gradeShadow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur in="SourceAlpha" stdDeviation="2" result="blur" />
        <feOffset in="blur" dx="0" dy="2" result="offsetBlur" />
        <feMerge>
            <feMergeNode in="offsetBlur" />
            <feMergeNode in="SourceGraphic" />
        </feMerge>
    </filter>
</defs>
<text x="${centerX}" y="${centerY}" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="${fontSize}" font-weight="500" fill="${txtColor}" dominant-baseline="middle" filter="url(#gradeShadow)">${escaped}</text>`;
                baseSvg = baseSvg.replace('</svg>', overlay + '</svg>');
    }
    return baseSvg;
}



    function generatePizzaSVG(radius, colors) {
        const centerX = radius;
        const centerY = radius;
        const slices = colors.length;
        const angleStep = 360 / slices;
    
        let svgPaths = '';
    
        for (let i = 0; i < slices; i++) {
        const startAngle = i * angleStep;
        const endAngle = (i + 1) * angleStep;
    
        const startX = centerX + radius * Math.cos((startAngle - 90) * Math.PI / 180);
        const startY = centerY + radius * Math.sin((startAngle - 90) * Math.PI / 180);
        const endX = centerX + radius * Math.cos((endAngle - 90) * Math.PI / 180);
        const endY = centerY + radius * Math.sin((endAngle - 90) * Math.PI / 180);
    
        const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1';
    
        svgPaths += `
            <path d="M ${centerX},${centerY} L ${startX},${startY} A ${radius},${radius} 0 ${largeArcFlag},1 ${endX},${endY} Z" 
                fill="${colors[i]}" />
        `;
        }
    
        return `
        <svg width="${radius * 2}" height="${radius * 2}" viewBox="0 0 ${radius * 2} ${radius * 2}" xmlns="http://www.w3.org/2000/svg">
            ${svgPaths}
        </svg>
        `;
    }
  
  



    var currentRouteStatusIconIndex = 0;
    var routeFinishStatus;

    // create an array with image names
    var images = ["1398911_correct_mark_success_tick_valid_icon.png",        // success icon 2
    "2682840_bolt_elictricity_light_lightning_storm_icon.png",   //flash icon 0
    "4125784_confounded_confused_emoji_emotion_fail_icon.png",    // attempt icon 1
    ];



    function resetFlashImage()
    {
            //console.log("resetFlashImage  "+ currentRouteStatusIconIndex);
            currentRouteStatusIconIndex = 0;
            routeFinishStatus = 'climbed';
            //document.getElementById('toggle-flash-image').src = "/public/images/316154_lightning_icon.png";
        var imgEl = document.getElementById('toggle-flash-image');
        if (imgEl) {
            imgEl.src = "/public/images/"+images[currentRouteStatusIconIndex];
        }
            
    }

    function toggleFlashImage()
    {
        //console.log("toggleFlashImage  "+ currentRouteStatusIconIndex);
        
        // advance to the next image index with every execution of this function
        currentRouteStatusIconIndex = (++currentRouteStatusIconIndex ) % images.length;
        // set the image source of oggle-flash-image to the image at the current index
        var imgEl = document.getElementById('toggle-flash-image');
        if (imgEl) {
            imgEl.src = "/public/images/"+images[currentRouteStatusIconIndex];
        }
        // set routeFinishStatus to flashed, attempt or success based on the current index
        if (currentRouteStatusIconIndex == 0)
        {
            routeFinishStatus = 'climbed';
        }
        else if (currentRouteStatusIconIndex == 1)
        {
            routeFinishStatus = 'flashed';
        }
        else if (currentRouteStatusIconIndex == 2)
        {
            routeFinishStatus = 'attempted';
        }
    }



       /**
     * Function to handle the DOMContentLoaded event.
     * 
     * Requirements for functioning properly:
     * - The HTML must include an input element with the id 'user-search'.
     * - The HTML must include a container element with the id 'suggestions' to display the search results.
     * - The server must have an endpoint '/api1/users/search' that accepts a query parameter 'q' and returns a JSON array of user objects.
     * - Each user object should have the following fields: firstname, lastname, nick, gpictureurl, fpictureurl, club, and id.
     */
    function loadUserLookAhead() {
        const userSearch = document.getElementById('user-search');
        const suggestions = document.getElementById('suggestions');
        const userIdField = document.getElementById('userId');

        // Named function to handle user input
        function handleUserInput() {
            const query = userSearch.value;

            if (query.length < 1) {
                suggestions.innerHTML = '';
                userSearch.dataset.userId = '';
                return;
            }

            apiFetch('/api1/users/search?q=' + encodeURIComponent(query))
                .then(response => response.json())
                .then(data => {

                    suggestions.innerHTML = '';
                    data.forEach(user => {
                        const suggestionItem = document.createElement('a');
                        suggestionItem.classList.add('list-group-item', 'list-group-item-action');
                        suggestionItem.href = '#';

                        const nick = user.nick ? `<i>(${user.nick})</i>` : '';

                        suggestionItem.innerHTML = `
                            <div class="media">
                                <img class="mr-3" src="${user.gpictureurl || user.fpictureurl || '/public/images/favicon.png'}" alt="${user.name}" width="40" height="40">
                                <div class="media-body">
                                    <h5 class="mt-0">${user.firstname} ${user.lastname} ${nick} - ${user.club}</h5>
                                </div>
                            </div>
                        `;
                        suggestionItem.addEventListener('click', function(event) {
                            event.preventDefault();
                            userSearch.value = `${user.firstname} ${user.lastname}`;
                            userSearch.dataset.userId = user.id;
                            userIdField.value = user.id;
                            suggestions.innerHTML = '';
                        });
                        suggestions.appendChild(suggestionItem);
                    });
                })
                .catch(error => console.error('Error fetching users:', error));
        }

        // Add event listener using the named function
        userSearch.addEventListener('input', handleUserInput);
    }





// Function to load the language pack
function loadLanguagePack(language = 'fr_FR', force = false) {
    return new Promise((resolve, reject) => {
        const storedTimestamp = localStorage.getItem('translations-timestamp');
        const storedLanguage = localStorage.getItem('translations-language');
        const currentTime = Date.now();
        const threeHoursInMillis = 3 * 60 * 60 * 1000;
        const storedTime = storedTimestamp ? new Date(storedTimestamp).getTime() : 0;
        const difference = currentTime - storedTime;

        if (storedLanguage !== language) {
            force = true;
        }
        if (!storedTimestamp || difference > threeHoursInMillis) {
            force = true;
        }

        if (force) {
            // Fetch the language pack from the API
            apiFetch('/api1/langpack/' + language)
                .then(response => response.json())
                .then(data => {
                    localStorage.setItem('translations', JSON.stringify(data));
                    localStorage.setItem('translations-timestamp', new Date().toISOString());
                    localStorage.setItem('translations-language', language);
                    replaceTranslations('loadLanguagePack');
                    resolve();
                })
                .catch(error => {
                    console.error('Error fetching language pack:', error);
                    reject(error);
                });
        } else {
            // Use cached translations if available
            try {
                const raw = localStorage.getItem('translations');
                if (raw) {
                    // Validate JSON to ensure it's an object
                    JSON.parse(raw);
                    replaceTranslations('loadLanguagePack not forced');
                } else {
                    console.warn('Translations cache empty; fetching language pack.');
                    return apiFetch('/api1/langpack/' + language)
                        .then(response => response.json())
                        .then(data => {
                            localStorage.setItem('translations', JSON.stringify(data));
                            localStorage.setItem('translations-timestamp', new Date().toISOString());
                            localStorage.setItem('translations-language', language);
                            replaceTranslations('loadLanguagePack fallback fetch');
                        })
                        .catch(err => console.error('Fallback fetch failed:', err))
                        .finally(() => resolve());
                }
                resolve();
            } catch (e) {
                console.warn('Invalid translations cache; refetching.', e);
                apiFetch('/api1/langpack/' + language)
                    .then(response => response.json())
                    .then(data => {
                        localStorage.setItem('translations', JSON.stringify(data));
                        localStorage.setItem('translations-timestamp', new Date().toISOString());
                        localStorage.setItem('translations-language', language);
                        replaceTranslations('loadLanguagePack invalid cache refetch');
                        resolve();
                    })
                    .catch(error => {
                        console.error('Error fetching language pack:', error);
                        reject(error);
                    });
            }
        }
    });
}




// Function to replace translations in the DOM
function replaceTranslations(id='') {
    let translations = null;
    //console.log('Replacing translations in DOM elements id='+id);
    try {
        const raw = localStorage.getItem('translations');
        translations = raw ? JSON.parse(raw) : null;
    } catch (e) {
        console.warn('Failed to parse translations from localStorage.', e);
        translations = null;
    }
    if (!translations || typeof translations !== 'object') {
        console.warn('No valid translations found in local storage.');
        return;
    }
    document.querySelectorAll('[data-translate-key]').forEach(element => {
        const key = element.getAttribute('data-translate-key');
        const value = translations[key];
        element.innerHTML = (value !== undefined && value !== null) ? value : key;
        //console.log(`Translated key: ${key} => ${element.innerHTML}`);
    });
}

function getTranslation(key) {
    try {
        const raw = localStorage.getItem('translations');
        if (!raw) {
            return key;
        }
        let stored = null;
        try {
            stored = JSON.parse(raw);
        } catch (e) {
            console.warn('Translations JSON parse error:', e);
            return key;
        }
        if (stored && typeof stored === 'object') {
            const value = stored[key];
            return (value !== undefined && value !== null) ? value : key;
        }
        return key;
    } catch (e) {
        console.warn('getTranslation error:', e);
        return key;
    }
}

// Function to clear translations from local storage
function clearTranslations() {
    console.log('Clearing translations from local storage');
    localStorage.removeItem('translations');
}




     // Function to show a Bootstrap alert 
     // requires a div with the id 'alertPlaceholder' in the HTML
     // this function should be called after the DOMContentLoaded event
     // it expects that translations are already loaded
     function showAlert(message, level, timeout=20000) {
        //console.log('showAlert:', message, level);
        const alertPlaceholder = document.getElementById('alertPlaceholder');
        // Create a span for the message
        const messageSpan = document.createElement('span');
        //messageSpan.setAttribute('data-translate-key', message);
        message = getTranslation(message);
        messageSpan.textContent = message;

        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${level} alert-dismissible fade show fixed-top-alert`;
        alertDiv.role = 'alert';
        // Create the close button
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close';
        closeButton.setAttribute('data-bs-dismiss', 'alert');
        closeButton.setAttribute('aria-label', 'Close');
      
        // Append the message span and close button to the alert div
        alertDiv.appendChild(messageSpan);
        alertDiv.appendChild(closeButton);

        if (alertPlaceholder !== undefined)
        {
            alertPlaceholder.className = 'text-center';
            alertPlaceholder.appendChild(alertDiv);
        }

        // Automatically remove the alert after 5 seconds
        if (timeout > 0) {
            setTimeout(() => {
                alertDiv.classList.remove('show');
                alertDiv.classList.add('fade');
                setTimeout(() => {
                    alertDiv.remove();
                }, 150); // Allow time for the fade-out transition
            }, 8000);
        }
    }



    // Function to get query parameters
    function getQueryParams() {
        const params = {};
        const queryString = window.location.search.substring(1);
        const queryArray = queryString.split('&');
        queryArray.forEach(param => {
            const [key, value] = param.split('=');
            params[key] = decodeURIComponent(value);
        });
        return params;
    }


         // Check for 'message' and 'level' query parameters and call showAlert
         document.addEventListener('DOMContentLoaded', () => {
            // Ensure logout elements trigger auth token clearing before navigation
            document.querySelectorAll('[data-logout="true"], a[href="/logout"], a[href="/api1/auth/logout"]').forEach(el => {
                el.addEventListener('click', () => {
                    try { clearJwtToken(); } catch (e) {}
                });
            });
            const queryParams = getQueryParams();
            const message = queryParams['message'];
            const top_notification_labelQP = app.top_notification_label || queryParams['top_notification_label'];
            const top_notification_levelQP = app.top_notification_level ||queryParams['top_notification_level'];

            //console.log('top_notification_label in skala util:'+ app.top_notification_label);

            if (top_notification_labelQP && top_notification_levelQP) {
                showAlert(top_notification_labelQP, top_notification_levelQP);
                
                  // Remove query parameters from the URL
                  const url = new URL(window.location);
                //url.searchParams.delete('message');
                url.searchParams.delete('top_notification_level');
                url.searchParams.delete('top_notification_label');
                window.history.replaceState({}, document.title, url.toString());
       
            }
        });

    function createAndRedirectToNewActiviity(gymId, activityName, activityDate) {

        // validate the inputs, if gym id is none then return, if activity name is empty then set it to 'New Activity', if activity date is empty then set it to today's date
        if (!gymId) {
            console.error('Gym ID is required to create a new activity.');

        }
        if (!activityName) {
            activityName = 'New Activity';
        }
        if (!activityDate) {
            const today = new Date();
            activityDate = today.toISOString().split('T')[0];
        }
        
        const data = {
            gym_id: gymId,
            activity_name: activityName,
            date: activityDate
        };


        fetch('/api1/activity', {
            method: 'POST',
            headers: {
            'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                //console.log('error response',response.json)
                //return Promise.reject(response);
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // redirect to the new activity page
            window.location.href = "/activities/"+data.id;
    
        })
        .catch(error => {
            console.error('catch error:', error);
            document.getElementById('hidden_message').textContent="{{ reference_data['current_language']['error5315'] }}";

            
            
        });
    }
