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
