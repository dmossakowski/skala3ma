
function getColorByBgColor(bgColor) 
{
 if (!bgColor) { return ''; }
  return (parseInt(bgColor.replace('#', ''), 16) > 0xffffff / 2) ? '#000' : '#fff';
}     



    
function getColorSVGDiv(color, colorModifier, width, height){
    var svg = getColorSVG(color, colorModifier);
    return `<div style='padding: 0px; margin: 0px 0px 0px 0px; width:${width}; height:${height}; border: 0px solid black; background-color: ${color}'> 
        ${svg}  </div>`
}

function getColorSVG(color, colorModifier){    

          //console.log(colorModifier);
    var svg = '';
//<?xml version="1.0" encoding="utf-8"?>
          // Check if the color modifier is 'marble' to apply the hatched pattern
    if (colorModifier === 'marble') {
      opposite_color = (Number(`0x1${color.slice(1)}`) ^ 0xFFFFFF).toString(16).substr(1).toUpperCase()
      //console.log(opposite_color);
      //console.log(cell.getValue());
      highlight = '#BBBBBB'
      stroke = getColorByBgColor(color)
      //highlight = `#${opposite_color}`;
      /*svg7 = `<svg viewBox="100 100 200 100" xmlns="http://www.w3.org/2000/svg">
<path style="fill: rgb(216, 216, 216); fill-opacity: 0; stroke: ${stroke};stroke-width: 2px;" d="M 89.356 95.09 C 89.356 108.955 106.641 113.076 115.695 105.821 C 126.656 97.04 111.914 87.9 104.167 87.9" transform="matrix(1, 0, 0, 1, 7.105427357601002e-15, 0)"/>
<path style="fill: rgb(216, 216, 216); fill-opacity: 0; stroke:  ${stroke};stroke-width: 2px;" d="M 86.947 116.437 C 98.057 117.836 113.652 124.371 123.771 115.331 C 125.942 113.392 128.06 110.785 129.227 108.139 C 131.696 102.543 129.928 80.932 142.53 87.458 C 143.867 88.151 146.589 89.002 147.206 90.515 C 148.291 93.172 147.025 97.397 146.774 100.092 C 144.919 120.029 128.823 130.623 109.235 131.419 C 102.731 131.684 86.304 135.168 86.304 124.901" transform="matrix(1, 0, 0, 1, 7.105427357601002e-15, 0)"/>
<path style="fill: rgb(216, 216, 216); fill-opacity: 0; stroke: ${stroke};stroke-width: 2px;" d="M 87.823 142.115 C 107.248 142.115 128.331 145.17 142.095 127.487 C 144.61 124.256 148.385 119.479 149.903 115.807 C 153.547 106.99 154.512 82.316 169.919 85.906 C 173.268 86.686 172.87 94.508 172.87 96.802 C 172.87 108.01 166.384 119.819 160.658 129.102 C 145.292 154.013 110.251 164.021 84.421 152.245" transform="matrix(1, 0, 0, 1, 7.105427357601002e-15, 0)"/>
<path style="fill: rgb(216, 216, 216); fill-opacity: 0; stroke: ${stroke};stroke-width: 2px;" d="M 89.629 176.892 C 117.671 176.892 151.817 163.246 164.915 136.777 C 169.941 126.619 174.846 116.643 178.109 105.696 C 181.41 94.617 182.546 78.293 198.398 80.583 C 205.758 81.646 205.798 90.065 205.798 95.611 C 205.798 111.043 200.218 123.133 190.617 135.466 C 183.014 145.232 172.365 157.295 162.061 164.379 C 153.415 170.323 142.257 172.851 132.347 175.661 C 117.637 179.83 102.945 184.284 87.367 184.284" transform="matrix(1, 0, 0, 1, 7.105427357601002e-15, 0)"/>
<path style="fill: rgb(216, 216, 216); fill-opacity: 0; stroke: ${stroke};stroke-width: 2px;" d="M 102.888 203.811 C 146.032 203.811 185.433 181.59 204.926 142.981 C 211.979 129.012 215.092 113.056 222.016 98.907 C 223.582 95.709 226.574 86.709 230.206 85.235 C 245.786 78.91 259.862 85.828 258.58 103.938 C 258.252 108.578 254.822 113.425 252.912 117.542 C 240.458 144.384 212.284 170.382 187.949 186.513 C 170.222 198.263 151.142 207.456 130.896 213.965 C 123.788 216.25 116.079 215.797 108.697 215.797 C 107.664 215.797 101.635 215.142 101.534 216.483" transform="matrix(1, 0, 0, 1, 7.105427357601002e-15, 0)"/>
<path style="fill: rgb(216, 216, 216); fill-opacity: 0; stroke: ${stroke};stroke-width: 2px;" d="M 280.176 223.813 C 275.426 223.151 271.755 220.542 267.795 217.895 C 245.546 203.025 257.037 186.396 263.097 165.851 C 264.848 159.917 264.679 153.35 266.472 147.636 C 267.926 143.003 264.677 134.685 264.669 129.589 C 264.655 120.776 261.246 91.708 274.973 90.392 C 287.079 89.231 275.608 112.052 275.608 117.716 C 275.608 125.558 278.446 133.045 277.962 140.987 C 276.768 160.575 266.235 178.174 280.272 195.771 C 282.526 198.596 288.677 205.802 292.568 205.926" transform="matrix(1, 0, 0, 1, 7.105427357601002e-15, 0)"/>
<path style="fill: rgb(216, 216, 216); fill-opacity: 0; stroke: ${stroke};stroke-width: 2px;" d="M 308.041 203.63 C 281.282 196.996 284.672 163.37 287.592 144.425 C 288.779 136.728 287.543 128.12 288.189 120.34 C 288.8 112.967 287.714 105.427 289 98.108 C 289.336 96.196 290.137 91.581 292.563 91.164 C 293.954 90.926 297.287 90.774 297.986 92.321 C 299.449 95.561 295.987 98.741 295.47 101.705 C 294.043 109.88 294.484 118.652 293.604 126.941 C 292.066 141.423 287.465 165.671 295.48 178.529 C 299.652 185.223 306.291 188.748 312.626 192.872" transform="matrix(1, 0, 0, 1, 7.105427357601002e-15, 0)"/>
</svg>`*/
            
      svg6 = `<svg viewBox="100 100 200 100" xmlns="http://www.w3.org/2000/svg">
<rect x="100.148" y="99.984" width="200.296" height="99.984" style="fill: ${color}; stroke: ${color};" transform="matrix(1, 0, 0, 1, 7.105427357601002e-15, 0)"/>

<path style="fill: rgb(216, 216, 216); fill-opacity: 0; stroke: ${stroke};stroke-width: 2px;" d="M 77.193 91.531 C 77.193 109.778 102.147 123.635 117.499 111.965 C 123.743 107.219 129.691 93.485 127.26 85.532 C 126.25 82.23 121.835 74.307 124.162 70.827 C 127.742 65.475 139.972 61.215 143.302 68.738 C 156.537 98.636 125.931 136.604 94.093 130.521 C 86.765 129.121 80.617 124.785 75.817 119.177 C 73.229 116.153 71.497 111.402 67.746 109.575" transform="matrix(1, 0, 0, 1, 7.105427357601002e-15, 0)"/>
<path style="fill: rgb(216, 216, 216); fill-opacity: 0; stroke: ${stroke};stroke-width: 2px;" d="M 76.754 135.251 C 84.848 136.199 93.444 140.298 101.495 142.31 C 116.049 145.949 132.345 136.168 142.028 126.021 C 159.535 107.674 156.859 62.071 191.822 64.965 C 195.701 65.286 197.557 71.397 195.73 74.405 C 192.708 79.381 186.724 82.812 184.287 88.072 C 179.181 99.089 178.529 116.824 170.636 126.277 C 166.252 131.528 163.216 137.127 157.515 141.284 C 133.843 158.545 87.714 157.701 65.25 139.712" transform="matrix(1, 0, 0, 1, 7.105427357601002e-15, 0)"/>
<path style="fill: rgb(216, 216, 216); fill-opacity: 0; stroke: ${stroke};stroke-width: 2px;" d="M 89.245 164.007 C 104.326 164.007 119.367 166.359 134.362 164.217 C 146.192 162.527 157.934 153.952 167.078 146.921 C 183.346 134.413 187.523 113.774 200.39 98.941 C 211.672 85.933 236.782 80.072 253.375 82.625 C 254.8 82.844 259.384 87.455 257.054 88.612 C 243.9 95.145 224.82 84.474 220.667 102.946 C 218.104 114.343 222.418 131.852 214.998 141.653 C 209.978 148.286 201.364 151.333 194.588 155.707 C 159.581 178.302 118.16 176.363 77.476 176.363" transform="matrix(1, 0, 0, 1, 7.105427357601002e-15, 0)"/>
<path style="fill: rgb(216, 216, 216); fill-opacity: 0; stroke: ${stroke};stroke-width: 2px;" d="M 89.356 184.584 C 128.683 184.584 163.502 187.314 198.171 166.407 C 206.261 161.528 214.549 156.915 220.421 149.307 C 228.457 138.893 230.463 126.235 236.64 114.872 C 248.588 92.892 275.957 85.981 299.246 85.981 C 311.095 85.981 330.649 93.379 325.308 109.31 C 324.388 112.051 322.872 115.357 321.051 117.68 C 319.054 120.229 315.74 124.849 312.831 126.168 C 308.602 128.086 302.48 124.489 298.804 123.095 C 286.542 118.446 277.708 107.857 262.977 114.071 C 253.264 118.167 250.764 129.932 246.944 138.667 C 240.607 153.155 231.044 171.107 216.188 178.478 C 192.176 190.393 163.542 190.041 143.153 209.001 C 140.01 211.924 127.831 220.402 127.762 225.029" transform="matrix(1, 0, 0, 1, 7.105427357601002e-15, 0)"/>
<path style="fill: rgb(216, 216, 216); fill-opacity: 0; stroke: ${stroke};stroke-width: 2px;" d="M 228.595 212.065 C 231.925 206.883 236.4 202.228 239.102 196.64 C 247.665 178.933 252.681 153.218 273.809 145.77 C 288.194 140.698 308.841 137.458 323.654 142.105 C 330.666 144.305 338.776 148.109 336.739 156.96 C 335.908 160.571 329.159 160.489 326.614 160.359 C 322.642 160.156 319.377 157.408 315.643 156.373 C 309.227 154.595 301.448 154.909 294.847 155.304 C 276.482 156.402 268.288 167.749 266.154 184.591 C 265.424 190.346 262.867 196.762 264.512 202.693 C 266.463 209.727 272.976 213.716 276.067 220.119" transform="matrix(1, 0, 0, 1, 7.105427357601002e-15, 0)"/>
<path style="fill: rgb(216, 216, 216); fill-opacity: 0; stroke: ${stroke};stroke-width: 2px;" d="M 299.371 219.588 C 284.706 219.588 275.149 195.922 278.72 183.883 C 283.16 168.912 305.219 164.832 318.376 166.38 C 323.227 166.951 328.192 176.461 322.746 179.248 C 309.457 186.05 293.348 169.444 288.925 190.127 C 286.352 202.157 311.355 212.755 319.359 215.206 C 322.604 216.199 324.945 217.666 327.797 219.484" transform="matrix(1, 0, 0, 1, 7.105427357601002e-15, 0)"/>
</svg>`

    // stick figure
   /*svg5 = `<?xml version="1.0" encoding="utf-8"?>
<svg viewBox="100 100 200 100" xmlns="http://www.w3.org/2000/svg">
<path style="fill: #${opposite_color}; stroke: #${opposite_color};" d="M 114.068 114.261 C 114.068 116.806 114.068 119.351 114.068 121.895 C 114.068 123.909 114.068 125.922 114.068 127.936 C 114.068 129.55 114.068 131.164 114.068 132.779 C 114.068 133.217 113.51 151.122 113.974 151.26 C 119.559 152.918 127.163 151.653 132.928 151.653 C 147.885 151.653 162.785 150.214 177.5 150.214 C 182.244 150.214 186.837 151.306 191.406 152.141 C 193.145 152.459 195.915 149.507 196.611 151.132 C 203.495 167.193 185.908 177.258 175.743 184.176 C 172.648 186.281 169.412 188.217 166.136 190.028 C 164.276 191.056 158.479 193.127 160.603 193.195 C 167.25 193.407 182.492 190.445 188.152 187.234 C 193.237 184.35 199.933 165.921 207.995 168.652 C 216.05 171.38 222.72 177.61 228.156 183.939 C 231.109 187.378 234.525 192.893 239.261 194.122 C 242.881 195.062 249.733 190.387 253.595 189.74 C 255.185 189.474 256.775 189.235 258.363 188.951 C 259.254 188.792 261.891 188.306 260.987 188.248 C 258.175 188.069 254.192 184.767 251.77 183.386 C 243.629 178.747 235.909 173.209 228.24 167.829 C 226.973 166.939 219.319 163.923 218.931 162.739 C 217.561 158.559 217.767 147.984 218.921 143.604 C 218.96 143.459 231.058 146.061 231.741 146.204 C 243.04 148.577 254.812 150.388 266.371 150.388 C 269.581 150.388 272.834 151.177 275.91 151.687 C 276.381 151.765 280.464 153.624 280.745 152.889 C 283.862 144.76 281.416 132.532 281.914 123.865 C 282.167 119.456 285.278 114.796 284.118 110.273 C 283.928 109.533 278.411 108.739 277.595 108.474 C 277.449 108.427 272.612 106.654 272.387 107.05 C 267.822 115.106 265.377 124.904 262.894 133.759 C 262.495 135.185 260.728 143.136 259.218 143.908 C 257.548 144.761 252.152 141.753 250.611 141.258 C 242.836 138.756 235.462 134.73 227.63 132.503 C 227 132.324 219.277 130.976 218.962 130.275 C 218.517 129.28 218.84 127.119 218.767 126.06 C 218.711 125.253 217.477 121.47 217.857 120.855 C 218.297 120.142 222.989 120.913 223.653 120.983 C 228.76 121.521 243.755 125.479 238.489 114.669 C 237.805 113.267 232.63 113.988 231.521 113.986 C 223.7 113.973 215.879 113.979 208.057 113.979 C 201.654 113.979 194.602 113.935 188.28 112.868 C 187.777 112.784 182.506 112.246 182.338 112.661 C 181.967 113.578 180.351 122.722 180.668 122.888 C 190.398 127.99 197.542 119.46 195.424 133.02 C 195.266 134.026 195.318 136.669 194.774 137.566 C 194.345 138.275 188.171 137.646 187.51 137.646 C 180.783 137.646 174.175 137.682 167.476 138.387 C 162.643 138.895 157.785 139.354 152.984 140.106 C 150.292 140.528 147.59 141.002 144.891 141.364 C 129.458 143.43 134.232 137.093 135.647 125.07 C 136.049 121.654 136.087 118.552 137.387 115.254 C 137.907 111.893 114.869 114.261 114.068 114.261 Z" transform="matrix(1, 0, 0, 1, 7.105427357601002e-15, 0)"/>
</svg>`*/
   
   
   

      //return `<div style='padding: 0px; margin: 0px 0px 0px 0px; width:${width}; height:${height}; border: 0px solid ${color}; background-color: ${color}'> 
        //${svg6}  </div>`
    return svg6;
  } else {
    svg0 = `<svg viewBox="100 100 200 100" xmlns="http://www.w3.org/2000/svg">
      <rect x="100.148" y="99.984" width="200.296" height="99.984" style="fill: ${color}; stroke: ${color};" transform="matrix(1, 0, 0, 1, 7.105427357601002e-15, 0)"/>
      </svg>`
    return svg0;

  }
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
        document.getElementById('toggle-flash-image').src = "/public/images/"+images[currentRouteStatusIconIndex];
        
}

    function toggleFlashImage()
    {
        //console.log("toggleFlashImage  "+ currentRouteStatusIconIndex);
        
        // advance to the next image index with every execution of this function
        currentRouteStatusIconIndex = (++currentRouteStatusIconIndex ) % images.length;
        // set the image source of oggle-flash-image to the image at the current index

        document.getElementById('toggle-flash-image').src = "/public/images/"+images[currentRouteStatusIconIndex];
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

            fetch('/api1/users/search?q=' + query)
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


let translations = {};

// Function to load the language pack
function loadLanguagePack(force = false) {
    return new Promise((resolve, reject) => {
        // Check if the language pack is in local storage and force is not true
        const storedTranslations = localStorage.getItem('translations');
        const storedTimestamp = localStorage.getItem('translations-timestamp');
        const currentTime = new Date().getTime();
        const threeHoursInMillis = 3 * 60 * 60 * 1000;
        const difference = currentTime - new Date(storedTimestamp).getTime()

        if (!storedTimestamp || difference > threeHoursInMillis) {
            force = true;   
        }

        if (storedTranslations && !force) {
            translations = JSON.parse(storedTranslations);
            //console.log('Language pack loaded from local storage:', translations['your_route_count'], difference);
            resolve();
        } else {
            // Fetch the language pack from the API
            fetch('/api1/langpack')
                .then(response => response.json())
                .then(data => {
                    translations = data;
                    // Store the language pack in local storage
                    localStorage.setItem('translations', JSON.stringify(translations));
                    //console.log('Language pack loaded:', translations);
                    localStorage.setItem('translations-timestamp', new Date().toISOString());
                    resolve();
                })
                .catch(error => {
                    console.error('Error fetching language pack:', error);
                    reject(error);
                });
        }
    });
}


// Function to replace translations in the DOM
function replaceTranslations() {
    document.querySelectorAll('[data-translate-key]').forEach(element => {
        const key = element.getAttribute('data-translate-key');
        element.innerHTML = translations[key] || key;
    });

    
}

function getTranslation(key) {
    //console.log('getTranslation:', key);

    t1 = JSON.parse(localStorage.getItem('translations'));
    //key='name'
    //console.log('t1:', t1);
    //console.log('t1:', t1[key]);
    //console.log('t2:', translations[key]);

    return translations[key] || key;
}

// Function to clear translations from local storage
function clearTranslations() {
    localStorage.removeItem('translations');
    translations = {};
}




     // Function to show a Bootstrap alert 
     // requires a div with the id 'alertPlaceholder' in the HTML
     function showAlert(message, level, timeout=8000) {
        //console.log('showAlert:', message, level);
        const alertPlaceholder = document.getElementById('alertPlaceholder');
        // Create a span for the message
        const messageSpan = document.createElement('span');
        messageSpan.setAttribute('data-translate-key', message);
        messageSpan.textContent = message;

        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${level} alert-dismissible fade show`;
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
            const queryParams = getQueryParams();
            const message = queryParams['message'];
            var label = queryParams['label']

                
            const level = queryParams['level'];

            if (label && level) {
                showAlert(label, level);

                  // Remove query parameters from the URL
                  const url = new URL(window.location);
                url.searchParams.delete('message');
                url.searchParams.delete('level');
                url.searchParams.delete('label');
                window.history.replaceState({}, document.title, url.toString());
       
            }
        });



