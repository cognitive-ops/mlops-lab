import express, { Request, Response } from 'express';
import cors from 'cors';
import 'dotenv/config';
import CodePipelineMetricsCollector, { PipelineMetrics, CodeBuildMetrics } from './codepipeline-collector';
import { logger } from './logger';

const app = express();
const port = process.env.PORT || 3000;
const metricsInterval = parseInt(process.env.METRICS_INTERVAL || '60000', 10);

// Middleware
app.use(cors());
app.use(express.json());

// Initialize metrics collector
const metricsCollector = new CodePipelineMetricsCollector();

// Store latest metrics in memory
let cachedMetrics: PipelineMetrics[] = [];
let cachedCodeBuildMetrics: CodeBuildMetrics[] = [];
let lastMetricsUpdateTime = new Date(0);
let lastCodeBuildMetricsUpdateTime = new Date(0);

// Health check endpoint
app.get('/health', (req: Request, res: Response) => {
  res.json({
    status: 'healthy',
    timestamp: new Date(),
    metricsUpdated: lastMetricsUpdateTime,
  });
});

// Get all pipeline metrics
app.get('/api/metrics', (req: Request, res: Response) => {
  try {
    res.json({
      success: true,
      data: cachedMetrics,
      lastUpdated: lastMetricsUpdateTime,
    });
  } catch (error) {
    logger.error('Error fetching metrics:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch metrics',
    });
  }
});

// Get metrics for a specific pipeline
app.get('/api/metrics/:pipelineName', (req: Request, res: Response) => {
  try {
    const { pipelineName } = req.params;
    const metrics = cachedMetrics.find(m => m.pipelineName === pipelineName);

    if (!metrics) {
      return res.status(404).json({
        success: false,
        error: `Pipeline '${pipelineName}' not found`,
      });
    }

    res.json({
      success: true,
      data: metrics,
      lastUpdated: lastMetricsUpdateTime,
    });
  } catch (error) {
    logger.error('Error fetching pipeline metrics:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch pipeline metrics',
    });
  }
});

// Get stage metrics for a specific pipeline
app.get('/api/metrics/:pipelineName/stages', (req: Request, res: Response) => {
  try {
    const { pipelineName } = req.params;
    const pipeline = cachedMetrics.find(m => m.pipelineName === pipelineName);

    if (!pipeline) {
      return res.status(404).json({
        success: false,
        error: `Pipeline '${pipelineName}' not found`,
      });
    }

    res.json({
      success: true,
      data: {
        pipelineName,
        stages: pipeline.stageMetrics,
        lastUpdated: lastMetricsUpdateTime,
      },
    });
  } catch (error) {
    logger.error('Error fetching stage metrics:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch stage metrics',
    });
  }
});

// Trigger metrics collection manually
app.post('/api/metrics/refresh', async (req: Request, res: Response) => {
  try {
    logger.info('Manual metrics refresh triggered');
    cachedMetrics = await metricsCollector.collectAndPublishAllMetrics();
    lastMetricsUpdateTime = new Date();

    res.json({
      success: true,
      message: 'Metrics refreshed successfully',
      data: cachedMetrics,
      lastUpdated: lastMetricsUpdateTime,
    });
  } catch (error) {
    logger.error('Error refreshing metrics:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to refresh metrics',
    });
  }
});

// List all available pipelines
app.get('/api/pipelines', async (req: Request, res: Response) => {
  try {
    const pipelines = await metricsCollector.listPipelines();
    res.json({
      success: true,
      data: pipelines,
    });
  } catch (error) {
    logger.error('Error listing pipelines:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to list pipelines',
    });
  }
});

// Get all CodeBuild projects
app.get('/api/codebuild/projects', async (req: Request, res: Response) => {
  try {
    const projects = await metricsCollector.listCodeBuildProjects();
    res.json({
      success: true,
      data: projects,
    });
  } catch (error) {
    logger.error('Error listing CodeBuild projects:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to list CodeBuild projects',
    });
  }
});

// Get all CodeBuild metrics
app.get('/api/codebuild/metrics', (req: Request, res: Response) => {
  try {
    res.json({
      success: true,
      data: cachedCodeBuildMetrics,
      lastUpdated: lastCodeBuildMetricsUpdateTime,
    });
  } catch (error) {
    logger.error('Error fetching CodeBuild metrics:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch CodeBuild metrics',
    });
  }
});

// Get metrics for a specific CodeBuild project
app.get('/api/codebuild/metrics/:projectName', (req: Request, res: Response) => {
  try {
    const { projectName } = req.params;
    const metrics = cachedCodeBuildMetrics.find(m => m.projectName === projectName);

    if (!metrics) {
      return res.status(404).json({
        success: false,
        error: `CodeBuild project '${projectName}' not found`,
      });
    }

    res.json({
      success: true,
      data: metrics,
      lastUpdated: lastCodeBuildMetricsUpdateTime,
    });
  } catch (error) {
    logger.error('Error fetching CodeBuild project metrics:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch CodeBuild project metrics',
    });
  }
});

// Refresh CodeBuild metrics
app.post('/api/codebuild/metrics/refresh', async (req: Request, res: Response) => {
  try {
    logger.info('Manual CodeBuild metrics refresh triggered');
    cachedCodeBuildMetrics = await metricsCollector.collectAndPublishAllCodeBuildMetrics();
    lastCodeBuildMetricsUpdateTime = new Date();

    res.json({
      success: true,
      message: 'CodeBuild metrics refreshed successfully',
      data: cachedCodeBuildMetrics,
      lastUpdated: lastCodeBuildMetricsUpdateTime,
    });
  } catch (error) {
    logger.error('Error refreshing CodeBuild metrics:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to refresh CodeBuild metrics',
    });
  }
});

// Get logs for a specific CodeBuild build
app.get('/api/codebuild/logs/:projectName/:buildId', async (req: Request, res: Response) => {
  try {
    const { projectName, buildId } = req.params;
    const logs = await metricsCollector.getBuildLogs(projectName, buildId);

    res.json({
      success: true,
      data: logs,
    });
  } catch (error) {
    logger.error('Error fetching CodeBuild logs:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch CodeBuild logs',
    });
  }
});

// Get the latest build logs for a project (optionally specify which build by index)
app.get('/api/codebuild/logs/:projectName', async (req: Request, res: Response) => {
  try {
    const { projectName } = req.params;
    const buildIndex = parseInt(req.query.buildIndex as string, 10) || 0;

    const logs = await metricsCollector.getProjectBuildLogs(projectName, buildIndex);

    res.json({
      success: true,
      data: logs,
    });
  } catch (error) {
    logger.error('Error fetching project build logs:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch project build logs',
    });
  }
});

// Get recent build logs for a project
app.get('/api/codebuild/logs/:projectName/recent', async (req: Request, res: Response) => {
  try {
    const { projectName } = req.params;
    const limit = parseInt(req.query.limit as string, 10) || 5;

    const logs = await metricsCollector.getRecentBuildLogs(projectName, limit);

    res.json({
      success: true,
      data: logs,
    });
  } catch (error) {
    logger.error('Error fetching recent build logs:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch recent build logs',
    });
  }
});

// Error handling middleware
app.use((err: any, req: Request, res: Response) => {
  logger.error('Unhandled error:', err);
  res.status(500).json({
    success: false,
    error: 'Internal server error',
  });
});

// Start periodic metrics collection
const startMetricsCollection = async () => {
  logger.info(`Starting metrics collection with interval: ${metricsInterval}ms`);

  const collectMetrics = async () => {
    try {
      logger.info('Collecting CodePipeline metrics...');
      cachedMetrics = await metricsCollector.collectAndPublishAllMetrics();
      lastMetricsUpdateTime = new Date();
      logger.info(`Successfully collected metrics for ${cachedMetrics.length} pipelines`);
    } catch (error) {
      logger.error('Error during scheduled metrics collection:', error);
    }
  };

  const collectCodeBuildMetrics = async () => {
    try {
      logger.info('Collecting CodeBuild metrics...');
      cachedCodeBuildMetrics = await metricsCollector.collectAndPublishAllCodeBuildMetrics();
      lastCodeBuildMetricsUpdateTime = new Date();
      logger.info(`Successfully collected metrics for ${cachedCodeBuildMetrics.length} CodeBuild projects`);
    } catch (error) {
      logger.error('Error during scheduled CodeBuild metrics collection:', error);
    }
  };

  // Collect metrics immediately on startup
  await collectMetrics();
  await collectCodeBuildMetrics();

  // Then schedule regular collection
  setInterval(collectMetrics, metricsInterval);
  setInterval(collectCodeBuildMetrics, metricsInterval);
};

// Start server
const startServer = async () => {
  try {
    await startMetricsCollection();

    app.listen(port, () => {
      logger.info(`CodePipeline Metrics API running on port ${port}`);
      logger.info(`Health check: http://localhost:${port}/health`);
      logger.info(`Metrics endpoint: http://localhost:${port}/api/metrics`);
    });
  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
};

startServer();

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM signal received: closing HTTP server');
  process.exit(0);
});

process.on('SIGINT', () => {
  logger.info('SIGINT signal received: closing HTTP server');
  process.exit(0);
});
