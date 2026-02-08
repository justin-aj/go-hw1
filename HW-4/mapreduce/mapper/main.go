package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/gin-gonic/gin"
)

var s3Client *s3.Client

func init() {
	cfg, err := config.LoadDefaultConfig(context.TODO(), config.WithRegion("us-east-1"))
	if err != nil {
		log.Fatalf("unable to load SDK config: %v", err)
	}
	s3Client = s3.NewFromConfig(cfg)
}

func main() {
	r := gin.Default()

	r.GET("/map", mapHandler)
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "healthy"})
	})

	r.Run(":8080")
}

func mapHandler(c *gin.Context) {
	bucket := c.Query("bucket")
	key := c.Query("key")
	outputKey := c.Query("output_key")

	if bucket == "" || key == "" || outputKey == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "bucket, key, and output_key query params required"})
		return
	}

	// 1. Download chunk from S3
	result, err := s3Client.GetObject(context.TODO(), &s3.GetObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to get S3 object: %v", err)})
		return
	}
	defer result.Body.Close()

	body, err := io.ReadAll(result.Body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to read body: %v", err)})
		return
	}

	text := string(body)

	// 2. Count word occurrences
	wordCounts := make(map[string]int)
	words := strings.Fields(text)
	for _, word := range words {
		cleaned := strings.ToLower(strings.Trim(word, ".,!?;:\"'()[]{}"))
		if cleaned != "" {
			wordCounts[cleaned]++
		}
	}

	// 3. Convert to JSON and upload to S3
	jsonData, err := json.Marshal(wordCounts)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to marshal JSON: %v", err)})
		return
	}

	_, err = s3Client.PutObject(context.TODO(), &s3.PutObjectInput{
		Bucket:      aws.String(bucket),
		Key:         aws.String(outputKey),
		Body:        strings.NewReader(string(jsonData)),
		ContentType: aws.String("application/json"),
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to upload results: %v", err)})
		return
	}

	// 4. Return output URL
	c.JSON(http.StatusOK, gin.H{
		"message":      "map complete",
		"output":       fmt.Sprintf("s3://%s/%s", bucket, outputKey),
		"unique_words": len(wordCounts),
		"total_words":  len(words),
	})
}
