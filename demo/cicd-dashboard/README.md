# CodePipeline Metrics API

A Node.js backend API for collecting and exposing AWS CodePipeline metrics with CloudWatch integration.

## Features

- **Real-time Metrics Collection**: Automatically collects metrics from all AWS CodePipeline pipelines
- **CloudWatch Integration**: Publishes custom metrics to CloudWatch for visualization and alerting
- **RESTful API**: Easy-to-use endpoints for retrieving pipeline and stage metrics
- **Health Checks**: Built-in health check endpoint for monitoring
- **Configurable Intervals**: Adjustable metrics collection frequency
- **Comprehensive Logging**: Winston-based logging with file and console output
- **CORS Support**: Ready for frontend integration

## Prerequisites

- Node.js 18+ and npm
- AWS credentials configured (via environment variables, IAM role, or AWS CLI)
- AWS permissions for:
  - `codepipeline:ListPipelines`
  - `codepipeline:GetPipelineState`
  - `cloudwatch:PutMetricData`

## Installation

```bash
npm install
```

## Configuration

Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

### Environment Variables

- `PORT`: Server port (default: 3000)
- `AWS_REGION`: AWS region for CodePipeline and CloudWatch (default: us-east-1)
- `LOG_LEVEL`: Logging level - debug, info, warn, error (default: info)
- `METRICS_INTERVAL`: Metrics collection interval in milliseconds (default: 60000)
- `AWS_ACCESS_KEY_ID`: AWS access key (optional, use IAM role or CLI config instead)
- `AWS_SECRET_ACCESS_KEY`: AWS secret key (optional, use IAM role or CLI config instead)

## Running the API

### Development

```bash
npm run dev
```

### Production

```bash
npm run build
npm start
```

## API Endpoints

### Health Check

```
GET /health
```

Returns server health status and last metrics update time.

### CodePipeline Endpoints

#### List All Pipelines

```
GET /api/pipelines
```

Returns a list of all available CodePipeline names in the AWS account.

#### Get All Metrics

```
GET /api/metrics
```

Returns cached metrics for all pipelines with the last update timestamp.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "pipelineName": "my-pipeline",
      "executionCount": 0,
      "successCount": 0,
      "failureCount": 0,
      "latestExecutionStatus": "Succeeded",
      "latestExecutionId": "abc123",
      "createdTime": "2023-01-01T00:00:00.000Z",
      "updatedTime": "2023-01-02T00:00:00.000Z",
      "stageMetrics": [
        {
          "stageName": "Source",
          "actionCount": 1,
          "successCount": 1,
          "failureCount": 0,
          "latestStatus": "Succeeded"
        }
      ]
    }
  ],
  "lastUpdated": "2023-01-02T12:00:00.000Z"
}
```

#### Get Specific Pipeline Metrics

```
GET /api/metrics/:pipelineName
```

Returns metrics for a specific pipeline.

#### Get Pipeline Stage Metrics

```
GET /api/metrics/:pipelineName/stages
```

Returns detailed stage metrics for a specific pipeline.

#### Refresh Metrics

```
POST /api/metrics/refresh
```

Manually trigger metrics collection and refresh.

### CodeBuild Endpoints

#### List All CodeBuild Projects

```
GET /api/codebuild/projects
```

Returns a list of all available CodeBuild project names in the AWS account.

**Response:**
```json
{
  "success": true,
  "data": [
    "project-1",
    "project-2",
    "project-3"
  ]
}
```

#### Get All CodeBuild Metrics

```
GET /api/codebuild/metrics
```

Returns cached metrics for all CodeBuild projects with the last update timestamp.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "projectName": "my-project",
      "source": "GITHUB",
      "serviceRole": "arn:aws:iam::ACCOUNT:role/codebuild-role",
      "lastModified": "2023-01-02T00:00:00.000Z",
      "buildCount": 25,
      "successCount": 23,
      "failureCount": 2,
      "lastBuildStatus": "SUCCEEDED",
      "lastBuildId": "my-project:abc123",
      "builds": [
        {
          "buildId": "my-project:abc123",
          "startTime": "2023-01-02T11:00:00.000Z",
          "endTime": "2023-01-02T11:05:00.000Z",
          "status": "SUCCEEDED",
          "duration": 5,
          "sourceVersion": "main"
        }
      ]
    }
  ],
  "lastUpdated": "2023-01-02T12:00:00.000Z"
}
```

#### Get Specific CodeBuild Project Metrics

```
GET /api/codebuild/metrics/:projectName
```

Returns metrics for a specific CodeBuild project, including recent build history.

#### Refresh CodeBuild Metrics

```
POST /api/codebuild/metrics/refresh
```

Manually trigger CodeBuild metrics collection and refresh.

### CodeBuild Logs Endpoints

#### Get Logs for Specific Build

```
GET /api/codebuild/logs/:projectName/:buildId
```

Returns CloudWatch logs for a specific CodeBuild build.

**Response:**
```json
{
  "success": true,
  "data": {
    "buildId": "my-project:abc123",
    "projectName": "my-project",
    "logGroupName": "/aws/codebuild/my-project",
    "logStreamName": "abc123",
    "logs": [
      {
        "timestamp": 1672677600000,
        "message": "Phase: DOWNLOAD_SOURCE"
      },
      {
        "timestamp": 1672677610000,
        "message": "Phase: INSTALL"
      }
    ]
  }
}
```

#### Get Latest Build Logs

```
GET /api/codebuild/logs/:projectName?buildIndex=0
```

Returns logs for a specific build of a project (defaults to latest build with buildIndex=0).

**Query Parameters:**
- `buildIndex` (optional): Index of the build in the recent builds list (0 = latest, 1 = second latest, etc.)

#### Get Recent Build Logs

```
GET /api/codebuild/logs/:projectName/recent?limit=5
```

Returns logs for multiple recent builds of a project.

**Query Parameters:**
- `limit` (optional): Number of recent builds to retrieve logs for (default: 5)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "buildId": "my-project:abc123",
      "projectName": "my-project",
      "logGroupName": "/aws/codebuild/my-project",
      "logStreamName": "abc123",
      "logs": [...]
    }
  ]
}
```

## Metrics Collected

### Pipeline-Level Metrics

- **PipelineExecutionLatency**: Execution count across stages

### Stage-Level Metrics

- **StageSuccessRate**: Percentage of successful actions in a stage
- **StageFailureCount**: Number of failed actions in a stage

### CodeBuild Metrics

- **ProjectBuildCount**: Total number of builds for a project
- **ProjectSuccessRate**: Percentage of successful builds
- **ProjectFailureCount**: Number of failed builds

### Custom Metrics in CloudWatch

**CodePipeline Metrics** - Namespace: `CodePipelineMetrics`
- Dimensions: `PipelineName`, `StageName`

**CodeBuild Metrics** - Namespace: `CodeBuildMetrics`
- Dimensions: `ProjectName`

## Docker Deployment

```bash
docker build -t codepipeline-metrics-api .
docker run -e AWS_REGION=us-east-1 -p 3000:3000 codepipeline-metrics-api
```

## Project Structure

```
src/
├── index.ts                      # Express server and API endpoints
├── codepipeline-collector.ts     # CodePipeline metrics collection logic
└── logger.ts                     # Winston logger configuration
```

## Logging

Logs are written to:
- **Console**: All levels with colors
- **logs/error.log**: Error level logs only
- **logs/combined.log**: All logs

## Error Handling

All API endpoints return a consistent error response format:

```json
{
  "success": false,
  "error": "Error description"
}
```

## Examples

### Fetch all metrics

```bash
curl http://localhost:3000/api/metrics
```

### Fetch specific pipeline metrics

```bash
curl http://localhost:3000/api/metrics/my-pipeline
```

### Get stage metrics

```bash
curl http://localhost:3000/api/metrics/my-pipeline/stages
```

### Manually refresh metrics

```bash
curl -X POST http://localhost:3000/api/metrics/refresh
```

### List CodeBuild projects

```bash
curl http://localhost:3000/api/codebuild/projects
```

### Get CodeBuild metrics

```bash
curl http://localhost:3000/api/codebuild/metrics
```

### Get specific CodeBuild project metrics

```bash
curl http://localhost:3000/api/codebuild/metrics/my-project
```

### Refresh CodeBuild metrics

```bash
curl -X POST http://localhost:3000/api/codebuild/metrics/refresh
```

### Get CodeBuild build logs

```bash
# Get logs for a specific build
curl http://localhost:3000/api/codebuild/logs/my-project/my-project:abc123

# Get logs for the latest build
curl http://localhost:3000/api/codebuild/logs/my-project

# Get logs for the second latest build
curl http://localhost:3000/api/codebuild/logs/my-project?buildIndex=1

# Get logs for the 5 most recent builds
curl http://localhost:3000/api/codebuild/logs/my-project/recent?limit=5
```

## Development

### Type Checking

```bash
npm run build
```

### Linting

```bash
npm run lint
```

## Future Enhancements

- [ ] Database persistence for historical metrics
- [ ] Advanced filtering and aggregation endpoints
- [ ] Webhook notifications for pipeline events
- [ ] Metrics visualization dashboard
- [ ] Cost analysis based on pipeline executions
- [ ] Integration with other AWS services (Lambda, EC2, etc.)

## License

MIT
