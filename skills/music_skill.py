import yt_dlp
import random

class EnhancedMusicSkill:
    def __init__(self):
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'extract_flat': 'in_playlist', # Better for radio/playlists
        }
        self.queue = []
        self.radio_mode = False
        self.current_genre = "lo-fi"
        
        self.RADIO_STATIONS = {
            "lo-fi": ["lofi hip hop radio", "chillhop live", "synthwave radio"],
            "jazz": ["coffee shop jazz live", "smooth jazz 24/7"],
            "rock": ["classic rock hits live", "90s rock radio"]
        }

    def get_stream(self, query: str):
        """The core engine that pulls the metadata"""
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            try:
                # If it's a short query, we use ytsearch
                search_query = f"ytsearch1:{query}" if not query.startswith("http") else query
                info = ydl.extract_info(search_query, download=False)
                
                if 'entries' in info:
                    video = info['entries'][0]
                else:
                    video = info

                return {
                    "title": video.get('title'),
                    "url": video.get('url'),
                    "thumbnail": video.get('thumbnail'),
                    "duration": video.get('duration'),
                    "id": video.get('id')
                }
            except Exception as e:
                return {"error": str(e)}

    def toggle_radio(self, genre: str = "lo-fi"):
        self.radio_mode = True
        self.current_genre = genre
        query = random.choice(self.RADIO_STATIONS.get(genre, self.RADIO_STATIONS["lo-fi"]))
        return self.get_stream(query)

# Initialize for FastAPI
music_engine = EnhancedMusicSkill()
