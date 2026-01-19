import { SQLiteDatabase } from '../src/services/database';
import { TimeEntry } from '../src/types';
import fs from 'fs';
import path from 'os';
import { describe, it, expect, beforeAll, afterAll, beforeEach } from '@jest/globals';

describe('Database', () => {
  let db: SQLiteDatabase;
  const testDbPath = `/tmp/timetracker-test-${Date.now()}.db`;

  beforeAll(async () => {
    // Clean up any existing test database
    if (fs.existsSync(testDbPath)) {
      fs.unlinkSync(testDbPath);
    }

    db = new SQLiteDatabase(testDbPath);
    await db.init();
  });

  afterAll(() => {
    db.close();
    if (fs.existsSync(testDbPath)) {
      fs.unlinkSync(testDbPath);
    }
  });

  beforeEach(async () => {
    // Clean up test data between tests
    const entries = await db.listTimeEntries();
    for (const entry of entries) {
      await db.deleteTimeEntry(entry.id);
    }
  });

  describe('Time Entries', () => {
    it('should create a time entry', async () => {
      const entryId = await db.createTimeEntry({
        start_time: Date.now(),
        project: 'TestProject',
        task: 'TestTask',
        notes: 'Test notes',
        git_commits: [],
        status: 'active',
      });

      expect(entryId).toBeDefined();
      expect(typeof entryId).toBe('string');

      const entry = await db.getTimeEntry(entryId);
      expect(entry).toBeDefined();
      expect(entry?.project).toBe('TestProject');
      expect(entry?.task).toBe('TestTask');
      expect(entry?.status).toBe('active');
    });

    it('should update a time entry', async () => {
      const entryId = await db.createTimeEntry({
        start_time: Date.now(),
        project: 'TestProject',
        status: 'active',
        git_commits: [],
      });

      await db.updateTimeEntry(entryId, {
        end_time: Date.now(),
        status: 'completed',
        notes: 'Completed task',
      });

      const entry = await db.getTimeEntry(entryId);
      expect(entry?.end_time).toBeDefined();
      expect(entry?.status).toBe('completed');
      expect(entry?.notes).toBe('Completed task');
    });

    it('should get active time entry', async () => {
      await db.createTimeEntry({
        start_time: Date.now(),
        project: 'ActiveProject',
        status: 'active',
        git_commits: [],
      });

      const activeEntry = await db.getActiveTimeEntry();
      expect(activeEntry).toBeDefined();
      expect(activeEntry?.status).toBe('active');
      expect(activeEntry?.project).toBe('ActiveProject');
    });

    it('should list time entries', async () => {
      await db.createTimeEntry({
        start_time: Date.now() - 10000,
        project: 'Project1',
        status: 'completed',
        end_time: Date.now() - 5000,
        git_commits: [],
      });

      await db.createTimeEntry({
        start_time: Date.now() - 3000,
        project: 'Project2',
        status: 'active',
        git_commits: [],
      });

      const entries = await db.listTimeEntries();
      expect(entries.length).toBeGreaterThanOrEqual(2);
    });

    it('should delete a time entry', async () => {
      const entryId = await db.createTimeEntry({
        start_time: Date.now(),
        project: 'ToDelete',
        status: 'active',
        git_commits: [],
      });

      await db.deleteTimeEntry(entryId);

      const entry = await db.getTimeEntry(entryId);
      expect(entry).toBeNull();
    });
  });

  describe('Projects', () => {
    it('should create a project', async () => {
      const projectId = await db.createProject({
        name: 'TestProject',
        description: 'A test project',
        directory_patterns: ['~/test/*'],
        git_repos: [],
      });

      expect(projectId).toBeDefined();

      const project = await db.getProject(projectId);
      expect(project?.name).toBe('TestProject');
      expect(project?.description).toBe('A test project');
    });

    it('should list projects', async () => {
      await db.createProject({
        name: 'Project1',
        directory_patterns: [],
        git_repos: [],
      });

      await db.createProject({
        name: 'Project2',
        directory_patterns: [],
        git_repos: [],
      });

      const projects = await db.listProjects();
      expect(projects.length).toBeGreaterThanOrEqual(2);
    });

    it('should update a project', async () => {
      const projectId = await db.createProject({
        name: 'OriginalName',
        directory_patterns: [],
        git_repos: [],
      });

      await db.updateProject(projectId, {
        name: 'UpdatedName',
        description: 'Updated description',
      });

      const project = await db.getProject(projectId);
      expect(project?.name).toBe('UpdatedName');
      expect(project?.description).toBe('Updated description');
    });

    it('should delete a project', async () => {
      const projectId = await db.createProject({
        name: 'ToDelete',
        directory_patterns: [],
        git_repos: [],
      });

      await db.deleteProject(projectId);

      const project = await db.getProject(projectId);
      expect(project).toBeNull();
    });
  });

  describe('Tasks', () => {
    it('should create a task', async () => {
      const projectId = await db.createProject({
        name: 'TaskProject',
        directory_patterns: [],
        git_repos: [],
      });

      const taskId = await db.createTask({
        project_id: projectId,
        name: 'TestTask',
        description: 'A test task',
        file_patterns: ['*.ts'],
      });

      expect(taskId).toBeDefined();

      const tasks = await db.listTasks(projectId);
      expect(tasks.length).toBe(1);
      expect(tasks[0].name).toBe('TestTask');
    });

    it('should list tasks for a project', async () => {
      const projectId = await db.createProject({
        name: 'TaskProject2',
        directory_patterns: [],
        git_repos: [],
      });

      await db.createTask({
        project_id: projectId,
        name: 'Task1',
      });

      await db.createTask({
        project_id: projectId,
        name: 'Task2',
      });

      const tasks = await db.listTasks(projectId);
      expect(tasks.length).toBe(2);
    });
  });

  describe('File Activities', () => {
    it('should log file activity', async () => {
      await db.logActivity({
        timestamp: Date.now(),
        file_path: '/test/file.ts',
        event_type: 'change',
        project_suggestion: 'TestProject',
      });

      const activities = await db.getRecentActivities(10);
      expect(activities.length).toBeGreaterThan(0);

      const activity = activities.find((a) => a.file_path === '/test/file.ts');
      expect(activity).toBeDefined();
      expect(activity?.event_type).toBe('change');
    });

    it('should get recent activities', async () => {
      await db.logActivity({
        timestamp: Date.now(),
        file_path: '/test/file1.ts',
        event_type: 'add',
      });

      await db.logActivity({
        timestamp: Date.now(),
        file_path: '/test/file2.ts',
        event_type: 'change',
      });

      const activities = await db.getRecentActivities(2);
      expect(activities.length).toBe(2);
    });
  });
});
