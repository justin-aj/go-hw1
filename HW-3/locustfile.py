from locust import HttpUser, task, between
import json
import random


class AlbumUser(HttpUser):
    """
    A user class that simulates interactions with the album API.
    Uses green threads (gevent) for lightweight concurrency.
    """
    
    # Target host (your Go server)
    host = "http://host.docker.internal:8080"
    
    # Wait time between tasks (simulates user "think time")
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """
        Called when a simulated user starts.
        Initialize any data needed for the test.
        """
        self.album_counter = 0
    
    @task(3)  # Weight of 3 - runs 3x more often than POST
    def get_albums(self):
        """
        GET request to retrieve all albums.
        This represents a read-heavy operation.
        """
        with self.client.get("/albums", name="GET /albums (all)", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    albums = response.json()
                    # Validate response has expected structure
                    if isinstance(albums, list):
                        response.success()
                    else:
                        response.failure("Response is not a list")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(1)  # Weight of 1 - runs 1x (less frequently)
    def post_album(self):
        """
        POST request to create a new album.
        This represents a write operation.
        """
        # Generate unique album data
        self.album_counter += 1
        new_album = {
            "id": f"locust-{self.album_counter}-{random.randint(1000, 9999)}",
            "title": f"Test Album {self.album_counter}",
            "artist": f"Test Artist {random.randint(1, 100)}",
            "price": round(random.uniform(9.99, 99.99), 2)
        }
        
        with self.client.post(
            "/albums",
            name="POST /albums (create)",
            json=new_album,
            catch_response=True
        ) as response:
            if response.status_code == 201:
                try:
                    created_album = response.json()
                    # Validate the created album matches what we sent
                    if created_album.get("id") == new_album["id"]:
                        response.success()
                    else:
                        response.failure("Created album doesn't match request")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(2)  # Weight of 2 - runs 2x
    def get_album_by_id(self):
        """
        GET request to retrieve a specific album by ID.
        Simulates targeted read operations.
        """
        # Try to get one of the seed albums
        album_id = random.choice(["1", "2", "3"])
        
        with self.client.get(f"/albums/{album_id}", name="GET /albums/:id (single)", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    album = response.json()
                    if album.get("id") == album_id:
                        response.success()
                    else:
                        response.failure("Album ID doesn't match")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Got status code {response.status_code}")


class GetOnlyUser(HttpUser):
    """
    A user class that only performs GET requests.
    Use this to test read-heavy scenarios.
    """
    host = "http://host.docker.internal:8080"
    wait_time = between(0.5, 2)
    
    @task
    def get_albums(self):
        """Only GET all albums."""
        self.client.get("/albums", name="GET /albums (read-only test)")


class PostOnlyUser(HttpUser):
    """
    A user class that only performs POST requests.
    Use this to test write-heavy scenarios.
    """
    host = "http://host.docker.internal:8080"
    wait_time = between(0.5, 2)
    
    def on_start(self):
        self.album_counter = 0
    
    @task
    def post_album(self):
        """Only POST new albums."""
        self.album_counter += 1
        new_album = {
            "id": f"write-test-{self.album_counter}",
            "title": f"Write Test {self.album_counter}",
            "artist": "Load Test Artist",
            "price": 29.99
        }
        self.client.post("/albums", name="POST /albums (write-only test)", json=new_album)
