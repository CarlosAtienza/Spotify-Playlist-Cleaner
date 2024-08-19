



function removeTrack(){
    //Remove track based on user
    const checkboxes = document.querySelectorAll('input[name="track"]:checked');
    const tracksToRemove = [];

    checkboxes.forEach((checkbox) => {
        tracksToRemove.push({
            uri: checkbox.value,
            name: checkbox.getAttribute('data-name')
        });
    });
    
    fetch('/remove-track', {
        method: 'POST',
        body: JSON.stringify({ tracks: tracksToRemove}),
    }).then((_res) => {
        window.location.href = "/";
    });
}

function deleteArtist(artistId){
    fetch('/delete-artist', {
        method: 'POST',
        body: JSON.stringify({ artistId: artistId}),

    }).then((_res) => {
        window.location.href = "/";
    });
}

