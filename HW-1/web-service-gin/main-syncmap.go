package main

import (
	"net/http"
	"sync"

	"github.com/gin-gonic/gin"
)

// album represents data about a record album.
type album struct {
	ID     string  `json:"id"`
	Title  string  `json:"title"`
	Artist string  `json:"artist"`
	Price  float64 `json:"price"`
}

// albums is a sync.Map for thread-safe concurrent access
// Key: string (album ID), Value: album struct
var albums sync.Map

func init() {
	// Seed initial album data
	seedAlbums := []album{
		{ID: "1", Title: "Blue Train", Artist: "John Coltrane", Price: 56.99},
		{ID: "2", Title: "Jeru", Artist: "Gerry Mulligan", Price: 17.99},
		{ID: "3", Title: "Sarah Vaughan and Clifford Brown", Artist: "Sarah Vaughan", Price: 39.99},
	}

	for _, a := range seedAlbums {
		albums.Store(a.ID, a)
	}
}

func main() {
	router := gin.Default()
	router.GET("/albums", getAlbums)
	router.POST("/albums", postAlbums)
	router.GET("/albums/:id", getAlbumByID)
	router.Run(":8080") // Allows external requests from the internet to reach your server
}

// getAlbums responds with the list of all albums as JSON.
// WARNING: sync.Map requires iterating with Range() - O(n) operation
// Getting all albums is still O(n), not O(1)!
// Trade-off: sync.Map optimizes individual lookups (O(1)) at the cost of
// requiring iteration for "get all" operations.
func getAlbums(c *gin.Context) {
	var albumList []album

	// Range iterates over all key-value pairs - O(n) complexity
	// This is still a read operation, and sync.Map optimizes concurrent reads,
	// but you must iterate through every entry to build the full list.
	albums.Range(func(key, value interface{}) bool {
		if a, ok := value.(album); ok {
			albumList = append(albumList, a)
		}
		return true // continue iteration
	})

	c.IndentedJSON(http.StatusOK, albumList)
}

// postAlbums adds an album from JSON received in the request body.
// sync.Map.Store() is thread-safe - no explicit locking needed!
func postAlbums(c *gin.Context) {
	var newAlbum album

	// Call BindJSON to bind the received JSON to newAlbum.
	if err := c.BindJSON(&newAlbum); err != nil {
		return
	}

	// Store is thread-safe - handles concurrent writes automatically
	albums.Store(newAlbum.ID, newAlbum)
	c.IndentedJSON(http.StatusCreated, newAlbum)
}

// getAlbumByID locates the album whose ID value matches the id
// parameter sent by the client, then returns that album as a response.
// This is O(1) with sync.Map - very fast!
func getAlbumByID(c *gin.Context) {
	id := c.Param("id")

	// Load is thread-safe and lock-free for existing keys
	if value, ok := albums.Load(id); ok {
		// Type assertion to convert interface{} to album
		if a, ok := value.(album); ok {
			c.IndentedJSON(http.StatusOK, a)
			return
		}
	}

	c.IndentedJSON(http.StatusNotFound, gin.H{"message": "album not found"})
}
