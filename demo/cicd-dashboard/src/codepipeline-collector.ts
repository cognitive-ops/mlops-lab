import { CodePipelineClient, ListPipelinesCommand, GetPipelineStateCommand } from '@aws-sdk/client-codepipeline';
import { CodeBuildClient, ListProjectsCommand, BatchGetProjectsCommand, ListBuildsForProjectCommand, BatchGetBuildsCommand } from '@aws-sdk/client-codebuild';
import { CloudWatchClient, PutMetricDataCommand } from '@aws-sdk/client-cloudwatch';
import { CloudWatchLogsClient, GetLogEventsCommand, DescribeLogGroupsCommand, DescribeLogStreamsCommand } from '@aws-sdk/client-cloudwatch-logs';
import { logger } from './logger';

export interface PipelineMetrics {
  pipelineName: string;
  executionCount: number;
  successCount: number;
  failureCount: number;
  latestExecutionStatus: string;
  latestExecutionId: string;
  createdTime: string;
  updatedTime: string;
  stageMetrics: StageMetric[];
}

export interface StageMetric {
  stageName: string;
  actionCount: number;
  successCount: number;
  failureCount: number;
  latestStatus: string;
}

export interface CodeBuildMetrics {
  projectName: string;
  source: string;
  serviceRole: string;
  lastModified: string;
  buildCount: number;
  successCount: number;
  failureCount: number;
  lastBuildStatus: string;
  lastBuildId: string;
  builds: BuildMetric[];
}

export interface BuildMetric {
  buildId: string;
  startTime: string;
  endTime: string;
  status: string;
  duration: number;
  sourceVersion: string;
}

export interface BuildLogs {
  buildId: string;
  projectName: string;
  logGroupName: string;
  logStreamName: string;
  logs: LogEvent[];
}

export interface LogEvent {
  timestamp: number;
  message: string;
}

class CodePipelineMetricsCollector {
  private codePipelineClient: CodePipelineClient;
  private codeBuildClient: CodeBuildClient;
  private cloudWatchClient: CloudWatchClient;
  private cloudWatchLogsClient: CloudWatchLogsClient;

  constructor() {
    const region = process.env.AWS_REGION || 'us-east-1';
    this.codePipelineClient = new CodePipelineClient({ region });
    this.codeBuildClient = new CodeBuildClient({ region });
    this.cloudWatchClient = new CloudWatchClient({ region });
    this.cloudWatchLogsClient = new CloudWatchLogsClient({ region });
  }

  async listPipelines(): Promise<string[]> {
    try {
      const command = new ListPipelinesCommand({});
      const response = await this.codePipelineClient.send(command);
      return response.pipelines?.map(p => p.name).filter(Boolean) as string[] || [];
    } catch (error) {
      logger.error('Error listing pipelines:', error);
      throw error;
    }
  }

  async getPipelineState(pipelineName: string): Promise<any> {
    try {
      const command = new GetPipelineStateCommand({ name: pipelineName });
      const response = await this.codePipelineClient.send(command);
      return response;
    } catch (error) {
      logger.error(`Error getting pipeline state for ${pipelineName}:`, error);
      throw error;
    }
  }

  async collectPipelineMetrics(pipelineName: string): Promise<PipelineMetrics> {
    try {
      const pipelineState = await this.getPipelineState(pipelineName);

      const stages = pipelineState.stageStates || [];
      const stageMetrics: StageMetric[] = stages.map((stage: any) => {
        const actions = stage.actionStates || [];
        const successCount = actions.filter((a: any) => a.latestExecution?.status === 'Succeeded').length;
        const failureCount = actions.filter((a: any) => a.latestExecution?.status === 'Failed').length;

        return {
          stageName: stage.stageName,
          actionCount: actions.length,
          successCount,
          failureCount,
          latestStatus: stage.latestExecution?.status || 'Unknown',
        };
      });

      const metrics: PipelineMetrics = {
        pipelineName,
        executionCount: 0,
        successCount: 0,
        failureCount: 0,
        latestExecutionStatus: pipelineState.latestExecution?.status || 'Unknown',
        latestExecutionId: pipelineState.latestExecution?.pipelineExecutionId || '',
        createdTime: pipelineState.created?.toISOString() || '',
        updatedTime: pipelineState.updated?.toISOString() || '',
        stageMetrics,
      };

      return metrics;
    } catch (error) {
      logger.error(`Error collecting metrics for pipeline ${pipelineName}:`, error);
      throw error;
    }
  }

  async publishMetricsToCloudWatch(metrics: PipelineMetrics): Promise<void> {
    try {
      const metricData: any[] = [];

      // Pipeline-level metrics
      metricData.push({
        MetricName: 'PipelineExecutionLatency',
        Value: metrics.stageMetrics.length > 0 ? metrics.stageMetrics.length * 100 : 0,
        Unit: 'Count',
        Timestamp: new Date(),
      });

      // Stage-level metrics
      metrics.stageMetrics.forEach(stage => {
        metricData.push({
          MetricName: 'StageSuccessRate',
          Value: stage.actionCount > 0 ? (stage.successCount / stage.actionCount) * 100 : 0,
          Unit: 'Percent',
          Dimensions: [
            { Name: 'PipelineName', Value: metrics.pipelineName },
            { Name: 'StageName', Value: stage.stageName },
          ],
          Timestamp: new Date(),
        });

        metricData.push({
          MetricName: 'StageFailureCount',
          Value: stage.failureCount,
          Unit: 'Count',
          Dimensions: [
            { Name: 'PipelineName', Value: metrics.pipelineName },
            { Name: 'StageName', Value: stage.stageName },
          ],
          Timestamp: new Date(),
        });
      });

      // Send metrics in batches (CloudWatch has a 20 metric limit per request)
      for (let i = 0; i < metricData.length; i += 20) {
        const batch = metricData.slice(i, i + 20);
        const command = new PutMetricDataCommand({
          Namespace: 'CodePipelineMetrics',
          MetricData: batch,
        });
        await this.cloudWatchClient.send(command);
      }

      logger.info(`Published metrics for pipeline: ${metrics.pipelineName}`);
    } catch (error) {
      logger.error('Error publishing metrics to CloudWatch:', error);
      throw error;
    }
  }

  async collectAndPublishAllMetrics(): Promise<PipelineMetrics[]> {
    try {
      const pipelines = await this.listPipelines();
      const allMetrics: PipelineMetrics[] = [];

      for (const pipelineName of pipelines) {
        const metrics = await this.collectPipelineMetrics(pipelineName);
        allMetrics.push(metrics);

        // Publish to CloudWatch
        await this.publishMetricsToCloudWatch(metrics);
      }

      return allMetrics;
    } catch (error) {
      logger.error('Error collecting and publishing metrics:', error);
      throw error;
    }
  }

  async listCodeBuildProjects(): Promise<string[]> {
    try {
      const command = new ListProjectsCommand({});
      const response = await this.codeBuildClient.send(command);
      return response.projects || [];
    } catch (error) {
      logger.error('Error listing CodeBuild projects:', error);
      throw error;
    }
  }

  async getCodeBuildProjectDetails(projectNames: string[]): Promise<any[]> {
    try {
      if (projectNames.length === 0) return [];

      const command = new BatchGetProjectsCommand({ names: projectNames });
      const response = await this.codeBuildClient.send(command);
      return response.projects || [];
    } catch (error) {
      logger.error('Error getting CodeBuild project details:', error);
      throw error;
    }
  }

  async getProjectBuilds(projectName: string, limit: number = 10): Promise<any[]> {
    try {
      const command = new ListBuildsForProjectCommand({
        projectName,
        sortOrder: 'DESCENDING',
      });
      const response = await this.codeBuildClient.send(command);
      const buildIds = (response.ids || []).slice(0, limit);

      if (buildIds.length === 0) return [];

      const buildsCommand = new BatchGetBuildsCommand({ ids: buildIds });
      const buildsResponse = await this.codeBuildClient.send(buildsCommand);
      return buildsResponse.builds || [];
    } catch (error) {
      logger.error(`Error getting builds for project ${projectName}:`, error);
      throw error;
    }
  }

  async collectCodeBuildMetrics(projectName: string): Promise<CodeBuildMetrics> {
    try {
      const projects = await this.getCodeBuildProjectDetails([projectName]);
      if (projects.length === 0) {
        throw new Error(`Project ${projectName} not found`);
      }

      const project = projects[0];
      const builds = await this.getProjectBuilds(projectName);

      const successCount = builds.filter((b: any) => b.buildStatus === 'SUCCEEDED').length;
      const failureCount = builds.filter((b: any) => b.buildStatus === 'FAILED').length;

      const buildMetrics: BuildMetric[] = builds.map((build: any) => ({
        buildId: build.id,
        startTime: build.startTime?.toISOString() || '',
        endTime: build.endTime?.toISOString() || '',
        status: build.buildStatus,
        duration: build.buildDurationInMinutes || 0,
        sourceVersion: build.sourceVersion || '',
      }));

      const metrics: CodeBuildMetrics = {
        projectName,
        source: project.source?.type || 'Unknown',
        serviceRole: project.serviceRole || '',
        lastModified: project.lastModified?.toISOString() || '',
        buildCount: builds.length,
        successCount,
        failureCount,
        lastBuildStatus: builds.length > 0 ? builds[0].buildStatus : 'Unknown',
        lastBuildId: builds.length > 0 ? builds[0].id : '',
        builds: buildMetrics,
      };

      return metrics;
    } catch (error) {
      logger.error(`Error collecting metrics for CodeBuild project ${projectName}:`, error);
      throw error;
    }
  }

  async publishCodeBuildMetricsToCloudWatch(metrics: CodeBuildMetrics): Promise<void> {
    try {
      const metricData: any[] = [];

      // Project-level metrics
      metricData.push({
        MetricName: 'ProjectBuildCount',
        Value: metrics.buildCount,
        Unit: 'Count',
        Dimensions: [{ Name: 'ProjectName', Value: metrics.projectName }],
        Timestamp: new Date(),
      });

      metricData.push({
        MetricName: 'ProjectSuccessRate',
        Value: metrics.buildCount > 0 ? (metrics.successCount / metrics.buildCount) * 100 : 0,
        Unit: 'Percent',
        Dimensions: [{ Name: 'ProjectName', Value: metrics.projectName }],
        Timestamp: new Date(),
      });

      metricData.push({
        MetricName: 'ProjectFailureCount',
        Value: metrics.failureCount,
        Unit: 'Count',
        Dimensions: [{ Name: 'ProjectName', Value: metrics.projectName }],
        Timestamp: new Date(),
      });

      // Send metrics in batches
      for (let i = 0; i < metricData.length; i += 20) {
        const batch = metricData.slice(i, i + 20);
        const command = new PutMetricDataCommand({
          Namespace: 'CodeBuildMetrics',
          MetricData: batch,
        });
        await this.cloudWatchClient.send(command);
      }

      logger.info(`Published CodeBuild metrics for project: ${metrics.projectName}`);
    } catch (error) {
      logger.error('Error publishing CodeBuild metrics to CloudWatch:', error);
      throw error;
    }
  }

  async collectAndPublishAllCodeBuildMetrics(): Promise<CodeBuildMetrics[]> {
    try {
      const projects = await this.listCodeBuildProjects();
      const allMetrics: CodeBuildMetrics[] = [];

      for (const projectName of projects) {
        const metrics = await this.collectCodeBuildMetrics(projectName);
        allMetrics.push(metrics);

        // Publish to CloudWatch
        await this.publishCodeBuildMetricsToCloudWatch(metrics);
      }

      return allMetrics;
    } catch (error) {
      logger.error('Error collecting and publishing CodeBuild metrics:', error);
      throw error;
    }
  }

  async getBuildLogs(projectName: string, buildId: string): Promise<BuildLogs> {
    try {
      // Extract the numeric part of buildId if it includes project name
      const cleanBuildId = buildId.includes(':') ? buildId.split(':')[1] : buildId;
      
      // CodeBuild log groups follow the pattern /aws/codebuild/{projectName}
      const logGroupName = `/aws/codebuild/${projectName}`;

      try {
        // Try to describe log groups to verify it exists
        await this.cloudWatchLogsClient.send(
          new DescribeLogGroupsCommand({ logGroupNamePrefix: logGroupName })
        );
      } catch (error) {
        logger.warn(`Log group ${logGroupName} not found`);
      }

      // Get log streams for this project
      let logStreams: any[] = [];
      try {
        const streamsResponse = await this.cloudWatchLogsClient.send(
          new DescribeLogStreamsCommand({
            logGroupName,
            orderBy: 'LastEventTime',
            descending: true,
            limit: 50,
          })
        );
        logStreams = streamsResponse.logStreams || [];
      } catch (error) {
        logger.warn(`Could not describe log streams for ${logGroupName}:`, error);
      }

      // Find the log stream that matches the build
      let logStreamName = '';
      if (logStreams.length > 0) {
        // Try to find exact match with buildId
        const matchedStream = logStreams.find(s => s.logStreamName?.includes(cleanBuildId));
        logStreamName = matchedStream?.logStreamName || logStreams[0].logStreamName || '';
      }

      const logs: LogEvent[] = [];

      if (logStreamName) {
        try {
          const logsResponse = await this.cloudWatchLogsClient.send(
            new GetLogEventsCommand({
              logGroupName,
              logStreamName,
              startFromHead: true,
            })
          );

          logs.push(
            ...(logsResponse.events?.map(event => ({
              timestamp: event.timestamp || 0,
              message: event.message || '',
            })) || [])
          );
        } catch (error) {
          logger.warn(`Could not get log events from ${logStreamName}:`, error);
        }
      }

      return {
        buildId,
        projectName,
        logGroupName,
        logStreamName,
        logs,
      };
    } catch (error) {
      logger.error(`Error getting logs for build ${buildId}:`, error);
      throw error;
    }
  }

  async getProjectBuildLogs(projectName: string, buildIndex: number = 0): Promise<BuildLogs> {
    try {
      // Get the most recent builds for the project
      const builds = await this.getProjectBuilds(projectName, 10);

      if (builds.length === 0 || buildIndex >= builds.length) {
        throw new Error(`No builds found for project ${projectName}`);
      }

      const build = builds[buildIndex];
      return this.getBuildLogs(projectName, build.id);
    } catch (error) {
      logger.error(`Error getting project build logs for ${projectName}:`, error);
      throw error;
    }
  }

  async getRecentBuildLogs(projectName: string, limitResults: number = 5): Promise<BuildLogs[]> {
    try {
      const builds = await this.getProjectBuilds(projectName, limitResults);
      const buildLogs: BuildLogs[] = [];

      for (const build of builds) {
        try {
          const logs = await this.getBuildLogs(projectName, build.id);
          buildLogs.push(logs);
        } catch (error) {
          logger.warn(`Failed to get logs for build ${build.id}:`, error);
        }
      }

      return buildLogs;
    } catch (error) {
      logger.error(`Error getting recent build logs for ${projectName}:`, error);
      throw error;
    }
  }
}

export default CodePipelineMetricsCollector;
