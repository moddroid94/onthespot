// utils.js
function capitalizeFirstLetter(string) {
    if (!string) return 'N/A';
    return string.charAt(0).toUpperCase() + string.slice(1);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
        .then(() => {
            console.log('Link copied to clipboard');
            // alert('Link copied to clipboard!');
        })
        .catch(err => {
            console.error('Failed to copy: ', err);
        });
}

function formatServiceName(serviceName) {
    const spacedServiceName = serviceName.replace(/_/g, ' ');

    const formattedServiceName = spacedServiceName.split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');

    return formattedServiceName;
}

function createButton(iconSrc, altText, onClickHandler, url = null) {
    if (url) {
        return `
            <button class="download-action-button" onclick="${onClickHandler}">
                <a href="${url}" onclick="event.preventDefault();">
                    <img src="${iconSrc}" loading="lazy" alt="${altText}">
                </a>
            </button>
        `;
    } else {
        return `
            <button class="download-action-button" onclick="${onClickHandler}">
                <img src="${iconSrc}" loading="lazy" alt="${altText}">
            </button>
        `;
    }
}
