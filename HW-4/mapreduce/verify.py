import json
import string
import boto3

BUCKET = "ajin-mapreduce-bucket"
REGION = "us-east-1"

s3 = boto3.client("s3", region_name=REGION)

# 1. Download and count words from the original file (single-machine approach)
print("=== Single-Machine Word Count ===")
obj = s3.get_object(Bucket=BUCKET, Key="shakespeare-hamlet.txt")
text = obj["Body"].read().decode("utf-8")

single_counts = {}
for word in text.split():
    cleaned = word.lower().strip(".,!?;:\"'()[]{}") 
    if cleaned:
        single_counts[cleaned] = single_counts.get(cleaned, 0) + 1

print(f"Total words: {sum(single_counts.values())}")
print(f"Unique words: {len(single_counts)}")

# 2. Download MapReduce result
print("\n=== MapReduce Word Count ===")
obj = s3.get_object(Bucket=BUCKET, Key="results/final_counts.json")
mr_counts = json.loads(obj["Body"].read().decode("utf-8"))

print(f"Total words: {sum(mr_counts.values())}")
print(f"Unique words: {len(mr_counts)}")

# 3. Compare
print("\n=== Comparison ===")
match = True

# Check if all words in single count are in MapReduce result
for word, count in single_counts.items():
    if word not in mr_counts:
        print(f"MISSING in MapReduce: '{word}' (count: {count})")
        match = False
    elif mr_counts[word] != count:
        print(f"MISMATCH: '{word}' -> single: {count}, mapreduce: {mr_counts[word]}")
        match = False

# Check if MapReduce has extra words
for word in mr_counts:
    if word not in single_counts:
        print(f"EXTRA in MapReduce: '{word}' (count: {mr_counts[word]})")
        match = False

if match:
    print("✅ PERFECT MATCH! MapReduce results are correct!")
else:
    print("❌ Results differ — check mismatches above")

# 4. Show top 10 words
print("\n=== Top 10 Words ===")
sorted_words = sorted(mr_counts.items(), key=lambda x: x[1], reverse=True)
for word, count in sorted_words[:10]:
    print(f"  {word}: {count}")