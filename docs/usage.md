<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../assets/01_Logo/Cover_White.png">
  <source media="(prefers-color-scheme: light)" srcset="../assets/01_Logo/Cover_Black.png">
  <img src="../assets/01_Logo/Cover_White.png" alt="Logo of OnTheSpot" width="350">
</picture>

<br>

# Getting Started

When launching the application for the first time you will receive a warning that no Spotify accounts are added.

1. **Dismiss the Warning**
   - Click the close button on the warning dialog.

2. **Add Your Spotify Account(s)**
   - Navigate to the **Configuration** tab.
   - Scroll to the bottom and add your Spotify account(s).

> [!TIP]
> Adding multiple accounts allows you to download multiple songs simultaneously, speeding up the download process.

[WIP: Youtube Video Explaining the Usage]

## 2. Searching and Downloading Music

### Search by Query

1. **Navigate to the Search Tab**
   - Click on the **Search** tab within the application.

2. **Enter Your Search Terms**
   - Type the name of a song, artist, album, or playlist into the search bar.

3. **Execute the Search**
   - Click the **Search** button to retrieve results.

4. **Download Music**
   - **Single Download**: Click the **Download** button next to the desired item.
   - **Bulk Download**: Use the buttons below the results table to download multiple items at once.

> [!NOTE]
> Downloading large media types like albums or playlists may take longer. The application might appear unresponsive during this process. Please be patient.

> [!TIP]
> You can also specify the path to a text file containing the links you want to download.

### Download by URL

1. **Enter the URL**
   - Paste the Spotify URL of a song, album, artist, or playlist into the search field.

2. **Start the Download**
   - Click the **Download** button to begin downloading.

3. **Bulk URL Downloads**
   - You can also provide a path to a text file containing multiple URLs. OnTheSpot will queue all listed URLs for downloading.

> [!IMPORTANT]
> Ensure each URL in the text file is on a separate line to avoid errors during the download process.

> [!NOTE]
> Similar to bulk downloads via query, downloading media types other than 'Tracks' may take longer and cause the app to appear frozen temporarily.

## 4. Configuration

Customize **OnTheSpot** to fit your preferences by adjusting the settings in the Configuration tab.

### General Configuration Options

> [!CAUTION]
> Changing some settings may affect the organization and quality of your downloaded music. Proceed with adjustments only if you are familiar with the options.

   <details open>
   <summary><b>Open Advanced Options</b></summary>

| **Option** | **Description** |
| ------ | ------ |
| **Download Path** | Root folder where all downloaded media will be saved. |
| **Theme** | Choose the application theme (`light` or `dark`). |
| **Download Buttons** | Adds extra functionalities like copying song links, opening tracks in your local music player, and locating the download directory. |
| **Show Thumbnails In Search/Downloads**| Display thumbnails on respective page. |
| **Thumbnail Size**|Change the size of thumbnail icons. |
| **Max Search Results** | Limits the number of search results displayed for each media type (e.g., songs, albums). |
| **Explicit Label** | Customize how explicit content is labeled in file names and the app (default: 🅴). |
| **Disable Bulk Download Notices** | Disables pop-up messages while downloading multiple songs or episodes. |
| **Mirror Spotify Playback** | Download currently playing song on the selected spotify account |
| **Windows 10 Explorer Thumbnails** | Embed thumbnails in a format that respects Windows 10 explorer and media player, this is an older format of ID3 and not widely supported. |
| **Close To Tray** | Close application to tray on exit. |
| **Check for Updates** | Automatically check for application updates. |
| **File Bitrate** | Set the bitrate of a converted file, default value is 320k. This setting is ignored if a lossless file format is selected. |
| **File Hertz** | Set the hertz of a converted file, default value is 44100 |
| **Track/Episode Format** | Select the audio format for your downloaded music or podcasts (e.g. `mp3`, `flac`, `ogg`, `m4a`). |
| [**Track/Episode Path**](#trackplaylist-path-format) | Customize the file naming pattern for tracks, episodes, and playlists using variables like `{artist}`, `{album}`, etc. |
| **Use Custom Playlist Path** | Enable the use of a custom path format for playlists. |
| [**Playlist Path**](#trackplaylist-path-format) | Customize the file naming pattern for playlists using variables like `{artist}`, `{album}`, etc. |
| **Create M3U Files for Playlists** | If enabled create an M3U file for downloaded tracks in a playlist. |
| [**M3U Path**](#trackplaylist-path-format) | Customize the download path of created M3U files using variables like `{artist}`, `{album}`, etc. |
| [**EXTINF Seperator**](#trackplaylist-path-format) | M3U EXTINF metadata / list seperator. |
| [**EXTINF Path**](#trackplaylist-path-format) | Customize the M3U EXTINF label using variables like `{artist}`, `{album}`, etc. |
| **Save Album Cover** | Save album cover as an image with a default format of cover.png |
| **Album Cover Format** | The image format to save album covers in (default: png) |
| **Illegal Character Replacement** | Replace illegal characters in the filepath with the value specified (e.g., `/`, `\`, `<`, `>`, `*`, etc.). |
| **Download Lyrics\*** | Enable downloading of lyrics for each track/episode. *This feature requires a premium account.* |
| **Download Synced Lyrics Only\*** | Only download synced lyrics for tracks. *This feature requires a premium account.*|
| **Save LRC File\*** | Save lyrics in an `.lrc` file alongside the track. *This feature requires a premium account.* |
| **Rotate Active Account** | Automatically rotate between added accounts for downloading to minimize the chance of hitting rate limits. |
| **Raw Media Download** | Downloads an unmodified file from whatever service is selected. With this enabled file conversion and the embedding of any metadata is skipped. |
| **Download Delay** | Time (in seconds) to wait before initiating the next download. Helps prevent Spotify's rate limits. |
| **Download Chunk Size** | The chunk size in which to download files. |
| **Maximum Queue Workers** | Set the maximum number of queue workers. Setting a higher number will queue songs faster, only change this setting if you know what you're doing. |
| **Maximum Download Workers** | Set the maximum number of download workers. Only change this setting if you know what you're doing. |
| **Translate File Path** | Translate file paths into the application language. |
| **Metadata Separator** | Set the separator for metadata fields with multiple values (default: `; `). |
| **Overwrite Existing Collection** | If a file already exists re-embed metadata in your selected format. |
| **Embed Metadata Tags** | Select which metadata tags to embed in downloaded files (e.g., `artist`, `album`, `year`, `lyrics`, etc.). |

   </details>


### Track/Episode/Playlist Path Format

- **Customize File Names**
  - Define how downloaded tracks are named using variables enclosed in `{}`.

- **Available Variables**

   <details open>
   <summary><b>Open Variables Table</b></summary>

   | **Variable**      | **Description**                                     |
   | ----------------- | --------------------------------------------------- |
   | `{service}`       | The music service used to download your file        |
   | `{artist}`        | Name of the artist(s).                              |
   | `{album_artist}`  | Name of the album artist(s).                        |
   | `{album_type}`    | Name of the artist type (single, album, etc).       |
   | `{album}`         | Name of the album.                                  |
   | `{name}`          | Name of the track.                                  |
   | `{year}`          | Release year of the track.                          |
   | `{track_number}`  | Track number on the album.                          |
   | `{trackcount}`    | Total number of tracks in the album                 |
   | `{disc_number}`   | Disc number (if applicable).                        |
   | `{discccount}`    | Total number of discs in the album (if applicable). |
   | `{genre}`         | Genre of the song.                                  |
   | `{label}`         | Name of the record label.                           |
   | `{explicit}`      | Displays 'Explicit Label' if the song is marked explicit (default: 🅴). |
   | `{playlist_name}` | Name of the playlist (if part of a playlist).       |
   | `{playlist_owner}`| Name of the playlist owner (if part of a playlist). |
   | `{playlist_number}`| Item number in a playlist (if part of a playlist). |
   </details>

> [!TIP]
> **Example:**
> Setting the format to `{artist} - {name}.mp3` will result in files named like `Artist Name - Song Title.mp3`.



## 6. Saving Your Configuration

- **Apply Changes**
  - After adjusting any settings, click the **Save Settings** button on the right to apply your changes.

> [!IMPORTANT]
> Some configuration changes may require restarting **OnTheSpot** to take effect. Make sure to restart the application if prompted.
