# Image Classification Cloud Application with Custom Autoscaling

## Overview
This project is an **Image Classification Cloud Application** built using AWS services. It allows users to upload images, which are then classified using a machine learning model. The architecture is designed to handle variable traffic with custom autoscaling capabilities, scaling the application between 0 to 20 instances based on demand.

## Architecture Diagram
![Architecture Diagram](https://github.com/user-attachments/assets/d687e207-5745-4eca-8f5a-0b73a7e61afd)

## Demo Video
[![Watch the video](https://img.youtube.com/vi/JXXCXUD-rVw/0.jpg)](https://youtu.be/JXXCXUD-rVw)


## Components

### 1. Users
- Multiple users (up to 50 or more) can upload images for classification.
- The system handles varying loads from different users efficiently.

### 2. Web Tier (AWS EC2 Instances)
- The **Web Tier** consists of **AWS EC2 instances** that handle incoming image upload requests from users.
- A **custom autoscaling code** dynamically scales the number of EC2 instances between **0 to 20**, depending on the traffic load.
- Uploaded images are processed here and sent to the next tier for classification.

### 3. AWS SQS (Simple Queue Service)
Two queues are used for communication between the Web Tier and App Tier:
- **SQS Request Queue**: Stores image classification requests in the form of `request_id` and `image_file_name`.
- **SQS Response Queue**: Stores classification results in the form of `request_id`, `image_file_name`, and `prediction_value`.

### 4. App Tier (AWS EC2 Instances)
- The **App Tier** consists of multiple EC2 instances running an **image recognition model**.
- These instances process images from the request queue and return classification results to the response queue.
- Like the Web Tier, this tier also scales between **0 to 20 instances** based on demand.

### 5. AWS S3 Buckets (Storage)
Two S3 buckets are used for storing images and results:
- **Input Bucket**: Stores uploaded images.
- **Output Bucket**: Stores classification results.

## Flow Summary
1. Users upload images for classification.
2. The Web Tier processes these requests and forwards them to the SQS Request Queue.
3. The App Tier processes these requests using an image recognition model.
4. Results are sent back through the SQS Response Queue and delivered to users.
5. Both input images and output results are stored in Amazon S3.

## Key Features
- **Custom Autoscaling**: Both Web and App Tiers can scale dynamically between 0 to 20 instances, optimizing resource usage based on traffic.
- **Queue-based Communication**: AWS SQS queues ensure reliable communication between tiers, enabling scalability.
- **Persistent Storage**: Amazon S3 provides durable storage for both input images and output results.

## Technologies Used
- AWS EC2 (Elastic Compute Cloud) for scalable compute resources.
- AWS SQS (Simple Queue Service) for managing request-response communication between tiers.
- AWS S3 (Simple Storage Service) for storing images and classification results.

## +++++ Test Result Statistics +++++
Total number of requests: 50 

Total number of requests completed successfully: 50

Total number of failed requests: 0

Total number of correct predictions : 50

Total number of wrong predictions: 0

Total Test Duration: 147.21658992767334 (seconds)

++++++++++++++++++++++++++++++++++++
