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

	r.GET("/reduce", reduceHandler)
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "healthy"})
	})

	r.Run(":8080")
}

func reduceHandler(c *gin.Context) {
	bucket := c.Query("bucket")
	keysParam := c.Query("keys")

	if bucket == "" || keysParam == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "bucket and keys query params required"})
		return
	}

	keys := strings.Split(keysParam, ",")

	// 1. Download and aggregate all mapper outputs
	finalCounts := make(map[string]int)

	for _, key := range keys {
		key = strings.TrimSpace(key)

		result, err := s3Client.GetObject(context.TODO(), &s3.GetObjectInput{
			Bucket: aws.String(bucket),
			Key:    aws.String(key),
		})
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to get %s: %v", key, err)})
			return
		}

		body, err := io.ReadAll(result.Body)
		result.Body.Close()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to read %s: %v", key, err)})
			return
		}

		var wordCounts map[string]int
		if err := json.Unmarshal(body, &wordCounts); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to parse %s: %v", key, err)})
			return
		}

		// Aggregate counts
		for word, count := range wordCounts {
			finalCounts[word] += count
		}
	}

	// 2. Save final result to S3
	outputKey := "results/final_counts.json"
	jsonData, err := json.Marshal(finalCounts)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to marshal final JSON: %v", err)})
		return
	}

	_, err = s3Client.PutObject(context.TODO(), &s3.PutObjectInput{
		Bucket:      aws.String(bucket),
		Key:         aws.String(outputKey),
		Body:        strings.NewReader(string(jsonData)),
		ContentType: aws.String("application/json"),
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("failed to upload final results: %v", err)})
		return
	}

	// 3. Return final output URL
	c.JSON(http.StatusOK, gin.H{
		"message":           "reduce complete",
		"output":            fmt.Sprintf("s3://%s/%s", bucket, outputKey),
		"unique_words":      len(finalCounts),
		"mappers_processed": len(keys),
	})
}
