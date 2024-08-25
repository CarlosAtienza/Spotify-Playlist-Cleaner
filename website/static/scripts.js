
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

function setupArtistSearch() {
    const artistInput = document.getElementById('artistsToRemove');
    const suggestions = document.getElementById('artistSuggestions');

    artistInput.addEventListener('input', function() {
        const query = this.value;
        if (query.length > 2) { // Start searching after 3 characters
            fetch(`/search_artist?q=${query}`)
                .then(response => response.json())
                .then(data => {
                    suggestions.innerHTML = ''; // Clear previous suggestions
                    data.forEach(artist => {
                        const option = document.createElement('div');
                        option.className = 'list-group-item';
                        option.textContent = artist.name;
                        option.onclick = function() {
                            artistInput.value = artist.name;
                            suggestions.innerHTML = ''; // Clear suggestions after selection
                        };
                        suggestions.appendChild(option);
                    });
                });
        } else {
            suggestions.innerHTML = ''; // Clear suggestions if query is too short
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    setupArtistSearch();
});
