'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useAuth, AgencyMembershipInfo } from '../../context/AuthContext';
import { useRouter } from 'next/navigation';

interface Client {
  id: string;
  name: string;
}

interface Project {
  id: string;
  name: string;
  description: string | null;
  client_id: string;
  client: Client;
}

interface User {
  id: string;
  email: string;
  full_name: string;
}

interface Task {
  id: string;
  title: string;
  description: string | null;
  status: string; // todo, in_progress, in_review, completed
  priority: string; // low, medium, high, urgent
  assignee_id: string | null;
  assignee?: User | null;
  due_date: string | null;
  is_client_visible: boolean;
}

interface DashboardMetrics {
  total_tasks: number;
  todo_tasks: number;
  in_progress_tasks: number;
  in_review_tasks: number;
  completed_tasks: number;
  total_hours_logged: number;
}

interface Comment {
  id: string;
  content: string;
  is_client_visible: boolean;
  user_id: string;
  author: User;
  created_at: string;
}

interface UploadedFile {
  id: string;
  filename: string;
  file_path: string;
  mime_type: string | null;
  file_size: number;
  is_client_visible: boolean;
  approval_status: string; // pending, approved, changes_requested
  uploader: User;
  created_at: string;
}

interface TimeEntry {
  id: string;
  duration_minutes: number;
  note: string | null;
  date: string;
  user_id: string;
  created_at: string;
}

interface ProjectMember {
  id: string;
  project_id: string;
  user: User;
}

interface AgencyMemberRecord {
  id: string;
  user: User;
  role: string;
  client_id: string | null;
}

interface IntakeForm {
  id: string;
  title: string;
  fields_schema: Record<string, unknown>;
  share_token: string;
  is_active: boolean;
}

interface NotificationItem {
  id: string;
  event_type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export default function DashboardPage() {
  const { user, activeMembership, isAuthenticated, loading, logout, switchAgency, apiFetch } = useAuth();
  const router = useRouter();

  // State
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [projectMembers, setProjectMembers] = useState<ProjectMember[]>([]);
  const [agencyMembers, setAgencyMembers] = useState<AgencyMemberRecord[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [intakeForms, setIntakeForms] = useState<IntakeForm[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  
  // Tab control
  const [activeTab, setActiveTab] = useState<'board' | 'team' | 'invites'>('board');
  
  // Selected Task inspection
  const [inspectedTask, setInspectedTask] = useState<Task | null>(null);
  const [taskComments, setTaskComments] = useState<Comment[]>([]);
  const [taskFiles, setTaskFiles] = useState<UploadedFile[]>([]);
  const [taskTimeEntries, setTaskTimeEntries] = useState<TimeEntry[]>([]);
  
  // Add modal states
  const [showAddProject, setShowAddProject] = useState(false);
  const [showAddTask, setShowAddTask] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showClientManager, setShowClientManager] = useState(false);
  const [showIntakeFormCreator, setShowIntakeFormCreator] = useState(false);
  
  // Form values
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');
  const [newProjectClientId, setNewProjectClientId] = useState('');
  const [newClientName, setNewClientName] = useState('');
  const [newIntakeTitle, setNewIntakeTitle] = useState('Project Intake');
  const [newIntakeFieldsJson, setNewIntakeFieldsJson] = useState('{\n  "budget": "text",\n  "timeline": "text",\n  "goals": "textarea"\n}');
  
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskDesc, setNewTaskDesc] = useState('');
  const [newTaskPriority, setNewTaskPriority] = useState('medium');
  const [newTaskAssignee, setNewTaskAssignee] = useState('');
  const [newTaskDueDate, setNewTaskDueDate] = useState('');
  const [newTaskClientVisible, setNewTaskClientVisible] = useState(false);

  const [newCommentText, setNewCommentText] = useState('');
  const [newCommentClientVisible, setNewCommentClientVisible] = useState(false);

  const [newTimeMinutes, setNewTimeMinutes] = useState(60);
  const [newTimeNote, setNewTimeNote] = useState('');

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('agency_member');
  const [inviteClientId, setInviteClientId] = useState('');
  const [inviteTokenGenerated, setInviteTokenGenerated] = useState('');

  const [newProjMemberId, setNewProjMemberId] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadClientVisible, setUploadClientVisible] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);

  // Redirect if guest
  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, loading, router]);

  // Load projects & agency data when membership changes
  useEffect(() => {
    if (isAuthenticated && activeMembership) {
      fetchProjects();
      if (activeMembership.role !== 'client_user') {
        fetchAgencyMembers();
        fetchClients();
        fetchIntakeForms();
      }
      fetchNotifications();
      // Clear selections
      setSelectedProject(null);
      setTasks([]);
      setMetrics(null);
      setInspectedTask(null);
    }
  }, [isAuthenticated, activeMembership]);

  // Fetch project details, metrics, tasks and members when a project is selected
  useEffect(() => {
    if (selectedProject) {
      fetchTasks(selectedProject.id);
      fetchDashboardMetrics(selectedProject.id);
      fetchProjectMembers(selectedProject.id);
      
      // If modal is open, reload that specific task to avoid stale data
      if (inspectedTask) {
        const found = tasks.find(t => t.id === inspectedTask.id);
        if (found) {
          setInspectedTask(found);
          fetchTaskDetails(found.id);
        } else {
          setInspectedTask(null);
        }
      }
    }
  }, [selectedProject]);

  // ----------------------------------------------------
  // API LOADERS
  // ----------------------------------------------------
  const fetchProjects = async () => {
    try {
      const res = await apiFetch('/projects');
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
        if (data.length > 0 && !selectedProject) {
          setSelectedProject(data[0]);
        }
      }
    } catch (err) {
      console.error('Failed to load projects:', err);
    }
  };

  const fetchTasks = async (projectId: string) => {
    try {
      const res = await apiFetch(`/tasks?project_id=${projectId}`);
      if (res.ok) {
        setTasks(await res.json());
      }
    } catch (err) {
      console.error('Failed to load tasks:', err);
    }
  };

  const fetchDashboardMetrics = async (projectId: string) => {
    try {
      const res = await apiFetch(`/dashboard/project/${projectId}`);
      if (res.ok) {
        setMetrics(await res.json());
      }
    } catch (err) {
      console.error('Failed to load dashboard metrics:', err);
    }
  };

  const fetchProjectMembers = async (projectId: string) => {
    try {
      const res = await apiFetch(`/projects/${projectId}/members`);
      if (res.ok) {
        setProjectMembers(await res.json());
      }
    } catch (err) {
      console.error('Failed to load project members:', err);
    }
  };

  const fetchAgencyMembers = async () => {
    try {
      const res = await apiFetch('/agencies/members');
      if (res.ok) {
        setAgencyMembers(await res.json());
      }
    } catch (err) {
      console.error('Failed to load agency members:', err);
    }
  };

  const fetchClients = async () => {
    try {
      const res = await apiFetch('/agencies/clients');
      if (res.ok) {
        setClients(await res.json());
      }
    } catch (err) {
      console.error('Failed to load clients:', err);
    }
  };

  const fetchIntakeForms = async () => {
    try {
      const res = await apiFetch('/intake-forms');
      if (res.ok) {
        setIntakeForms(await res.json());
      }
    } catch (err) {
      console.error('Failed to load intake forms:', err);
    }
  };

  const fetchNotifications = async () => {
    try {
      const res = await apiFetch('/notifications');
      if (res.ok) {
        setNotifications(await res.json());
      }
    } catch (err) {
      console.error('Failed to load notifications:', err);
    }
  };

  const fetchTaskDetails = async (taskId: string) => {
    try {
      // 1. Fetch Comments
      const commentsRes = await apiFetch(`/comments/task/${taskId}`);
      if (commentsRes.ok) {
        setTaskComments(await commentsRes.json());
      }

      // 2. Fetch Files
      const filesRes = await apiFetch(`/files/task/${taskId}`);
      if (filesRes.ok) {
        setTaskFiles(await filesRes.json());
      }

      // 3. Fetch Time Logs (only visible for agency users)
      if (activeMembership?.role !== 'client_user') {
        const timeRes = await apiFetch(`/time-entries/task/${taskId}`);
        if (timeRes.ok) {
          setTaskTimeEntries(await timeRes.json());
        }
      }
    } catch (err) {
      console.error('Failed to load task subcomponents:', err);
    }
  };

  const handleSelectTask = (task: Task) => {
    setInspectedTask(task);
    fetchTaskDetails(task.id);
  };

  // ----------------------------------------------------
  // MUTATIONS
  // ----------------------------------------------------
  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName || !newProjectClientId) return;

    try {
      const res = await apiFetch('/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newProjectName,
          description: newProjectDesc || null,
          client_id: newProjectClientId
        })
      });

      if (res.ok) {
        setNewProjectName('');
        setNewProjectDesc('');
        setShowAddProject(false);
        await fetchProjects();
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || 'Could not create project.'}`);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const openCreateProject = () => {
    setShowAddProject(true);
    if (activeMembership?.role === 'agency_admin' && clients.length === 0) {
      setShowClientManager(true);
    }
  };

  const handleCreateClient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClientName.trim()) return;

    try {
      const res = await apiFetch('/agencies/clients', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newClientName })
      });

      if (res.ok) {
        setNewClientName('');
        setShowClientManager(false);
        await fetchClients();
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || 'Could not create client company.'}`);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateIntakeForm = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const parsedFields = JSON.parse(newIntakeFieldsJson);
      const res = await apiFetch('/intake-forms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newIntakeTitle,
          fields_schema: parsedFields,
          is_active: true
        })
      });

      if (res.ok) {
        setShowIntakeFormCreator(false);
        await fetchIntakeForms();
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || 'Could not create intake form.'}`);
      }
    } catch (err) {
      alert('Intake form schema must be valid JSON.');
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskTitle || !selectedProject) return;

    try {
      const res = await apiFetch('/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: selectedProject.id,
          title: newTaskTitle,
          description: newTaskDesc || null,
          priority: newTaskPriority,
          assignee_id: newTaskAssignee || null,
          due_date: newTaskDueDate ? new Date(newTaskDueDate).toISOString() : null,
          is_client_visible: newTaskClientVisible
        })
      });

      if (res.ok) {
        setNewTaskTitle('');
        setNewTaskDesc('');
        setNewTaskPriority('medium');
        setNewTaskAssignee('');
        setNewTaskDueDate('');
        setNewTaskClientVisible(false);
        setShowAddTask(false);
        
        // Refresh project data
        fetchTasks(selectedProject.id);
        fetchDashboardMetrics(selectedProject.id);
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || 'Could not create task.'}`);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleUpdateTaskStatus = async (taskId: string, newStatus: string) => {
    if (!selectedProject) return;
    try {
      const res = await apiFetch(`/tasks/${taskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });

      if (res.ok) {
        fetchTasks(selectedProject.id);
        fetchDashboardMetrics(selectedProject.id);
        // Refresh inspected task state if open
        if (inspectedTask && inspectedTask.id === taskId) {
          setInspectedTask({ ...inspectedTask, status: newStatus });
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddProjectMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProject || !newProjMemberId) return;

    try {
      const res = await apiFetch(`/projects/${selectedProject.id}/members`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: newProjMemberId })
      });

      if (res.ok) {
        setNewProjMemberId('');
        fetchProjectMembers(selectedProject.id);
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || 'Could not add member.'}`);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleRemoveProjectMember = async (targetUserId: string) => {
    if (!selectedProject) return;
    if (!confirm('Are you sure you want to remove this member from the project? Any tasks assigned to them in this project will be unassigned.')) return;

    try {
      const res = await apiFetch(`/projects/${selectedProject.id}/members/${targetUserId}`, {
        method: 'DELETE'
      });

      if (res.ok) {
        fetchProjectMembers(selectedProject.id);
        fetchTasks(selectedProject.id); // Reload tasks to see updated assignee states
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleRemoveAgencyMember = async (targetUserId: string) => {
    if (!confirm('WARNING: Removing this member deletes their agency access. All tasks assigned to them across the entire agency will be unassigned. Proceed?')) return;

    try {
      const res = await apiFetch(`/agencies/members/${targetUserId}`, {
        method: 'DELETE'
      });

      if (res.ok) {
        fetchAgencyMembers();
        if (selectedProject) {
          fetchProjectMembers(selectedProject.id);
          fetchTasks(selectedProject.id);
        }
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || 'Could not remove member.'}`);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inspectedTask || !newCommentText.trim()) return;

    try {
      const res = await apiFetch(`/comments?task_id=${inspectedTask.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: newCommentText,
          is_client_visible: activeMembership?.role === 'client_user' ? true : newCommentClientVisible
        })
      });

      if (res.ok) {
        setNewCommentText('');
        setNewCommentClientVisible(false);
        fetchTaskDetails(inspectedTask.id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const filesList = e.target.files;
    if (!filesList || filesList.length === 0 || !inspectedTask) return;

    setUploadingFile(true);
    const uploaded = filesList[0];
    const formData = new FormData();
    formData.append('task_id', inspectedTask.id);
    formData.append('file', uploaded);
    formData.append('is_client_visible', activeMembership?.role === 'client_user' ? 'true' : String(uploadClientVisible));

    try {
      const token = localStorage.getItem('token');
      const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const headers = new Headers();
      if (token) headers.set('Authorization', `Bearer ${token}`);
      if (activeMembership) headers.set('X-Agency-ID', activeMembership.agency_id);

      const res = await fetch(`${BACKEND_URL}/api/files`, {
        method: 'POST',
        headers,
        body: formData
      });

      if (res.ok) {
        fetchTaskDetails(inspectedTask.id);
      } else {
        const err = await res.json();
        alert(`Upload failed: ${err.detail || 'Max size exceeded or invalid file'}`);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setUploadingFile(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleFileApproval = async (fileId: string, newStatus: 'approved' | 'changes_requested') => {
    if (!inspectedTask) return;
    try {
      const res = await apiFetch(`/files/${fileId}/approval`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approval_status: newStatus })
      });

      if (res.ok) {
        fetchTaskDetails(inspectedTask.id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleLogTime = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inspectedTask || !newTimeMinutes || newTimeMinutes <= 0) return;

    try {
      const res = await apiFetch(`/time-entries?task_id=${inspectedTask.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          duration_minutes: newTimeMinutes,
          note: newTimeNote || null,
          date: new Date().toISOString().split('T')[0]
        })
      });

      if (res.ok) {
        setNewTimeMinutes(60);
        setNewTimeNote('');
        fetchTaskDetails(inspectedTask.id);
        if (selectedProject) {
          fetchDashboardMetrics(selectedProject.id); // Reload total hours metrics
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail) return;

    try {
      const res = await apiFetch('/invites', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: inviteEmail,
          role: inviteRole,
          client_id: inviteRole === 'client_user' ? inviteClientId : null
        })
      });

      if (res.ok) {
        const data = await res.json();
        setInviteTokenGenerated(data.token);
        setInviteEmail('');
        setInviteClientId('');
      } else {
        const err = await res.json();
        alert(`Invite failed: ${err.detail || 'Verify arguments.'}`);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Helpers
  const formatDuration = (mins: number) => {
    const hrs = Math.floor(mins / 60);
    const m = mins % 60;
    return hrs > 0 ? `${hrs}h ${m}m` : `${m} mins`;
  };

  if (loading || !isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#0b0f19]">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-t-transparent border-violet-500"></div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-[#080b13]">
      {/* ----------------------------------------------------
          NAVBAR HEADER
          ---------------------------------------------------- */}
      <header className="flex items-center justify-between px-6 py-4 bg-[#0d1220]/80 backdrop-blur-md border-b border-white/5 sticky top-0 z-50">
        <div className="flex items-center gap-6">
          <span className="text-xl font-black bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
            AgencyDesk
          </span>

          {/* Agency Tenant Switcher */}
          {user && user.memberships.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 font-semibold uppercase">Workspace:</span>
              <select
                value={activeMembership?.agency_id || ''}
                onChange={(e) => switchAgency(e.target.value)}
                className="bg-slate-900 border border-white/10 rounded-lg px-3 py-1.5 text-sm font-medium text-white focus:border-violet-500 outline-none cursor-pointer"
              >
                {user.memberships.map((m) => (
                  <option key={m.agency_id} value={m.agency_id}>
                    {m.agency_name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* User profile details & role indicators */}
        <div className="flex items-center gap-4">
          {activeMembership && (
            <span className={`badge ${
              activeMembership.role === 'agency_admin' ? 'badge-admin' :
              activeMembership.role === 'agency_member' ? 'badge-member' : 'badge-client'
            }`}>
              {activeMembership.role === 'agency_admin' ? 'Agency Owner' :
               activeMembership.role === 'agency_member' ? 'Agency Staff' : 
               `Client: ${activeMembership.client_name || 'Portal'}`}
            </span>
          )}

          <div className="text-right hidden sm:block">
            <div className="text-xs font-semibold text-white">{user?.full_name}</div>
            <div className="text-[10px] text-gray-400">{user?.email}</div>
          </div>

          <button
            onClick={logout}
            className="p-2 rounded-lg bg-slate-900 border border-white/5 hover:border-red-500/20 text-gray-400 hover:text-red-400 transition-all cursor-pointer"
            title="Log Out"
          >
            {/* Log out icon */}
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 01-3-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </header>

      {/* ----------------------------------------------------
          MAIN CONTENT WORKSPACE
          ---------------------------------------------------- */}
      <div className="flex flex-1 overflow-hidden">
        
        {/* SIDEBAR: PROJECTS */}
        <aside className="w-64 bg-[#0a0d18] border-r border-white/5 p-4 flex flex-col gap-4 hidden md:flex">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Projects</span>
            {activeMembership?.role === 'agency_admin' && (
              <button
                onClick={() => setShowAddProject(true)}
                className="p-1 rounded bg-violet-600/20 text-violet-400 hover:bg-violet-600 hover:text-white transition-all cursor-pointer"
                title="New Project"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
            )}
          </div>

          <div className="flex flex-col gap-1 overflow-y-auto flex-1">
            {projects.length === 0 ? (
              <div className="text-xs text-gray-500 italic p-3 text-center">No projects in workspace.</div>
            ) : (
              projects.map((proj) => (
                <button
                  key={proj.id}
                  onClick={() => setSelectedProject(proj)}
                  className={`w-full text-left p-3 rounded-xl transition-all flex flex-col gap-1 cursor-pointer border ${
                    selectedProject?.id === proj.id
                      ? 'bg-violet-950/20 border-violet-500/30 text-white'
                      : 'border-transparent text-gray-400 hover:bg-slate-900/60 hover:text-gray-300'
                  }`}
                >
                  <span className="text-sm font-semibold truncate">{proj.name}</span>
                  <span className="text-[10px] text-gray-500 truncate">
                    Client: {proj.client.name}
                  </span>
                </button>
              ))
            )}
          </div>
        </aside>

        {/* WORKSPACE AREA */}
        <main className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
          {activeMembership?.role === 'client_user' && (
            <div className="glass-panel p-6 border-emerald-500/20 bg-emerald-950/10">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-emerald-400 font-bold">Client Portal</div>
                  <h2 className="text-2xl font-black text-white mt-1">
                    Welcome, {activeMembership.client_name || 'Client'}
                  </h2>
                  <p className="text-sm text-gray-400 mt-1">
                    Your workspace is filtered to the projects, tasks, comments, and files shared with your company.
                  </p>
                </div>
                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
                  {projects.length} project{projects.length === 1 ? '' : 's'} available
                </div>
              </div>
            </div>
          )}

          {activeMembership?.role === 'agency_admin' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="glass-panel p-5 lg:col-span-2">
                <div className="flex items-center justify-between gap-4 mb-4">
                  <div>
                    <h3 className="text-base font-bold text-white">Client Companies</h3>
                    <p className="text-xs text-gray-400 mt-1">
                      Create the client company here first, then assign it to projects and invitations.
                    </p>
                  </div>
                  <button
                    onClick={() => setShowClientManager((current) => !current)}
                    className="btn-secondary text-xs py-1.5 px-3"
                  >
                    {showClientManager ? 'Hide Form' : 'New Client'}
                  </button>
                </div>

                <div className="flex flex-col gap-2">
                  {clients.length === 0 ? (
                    <div className="text-sm text-gray-500 italic">No client companies yet.</div>
                  ) : (
                    clients.map((client) => (
                      <div key={client.id} className="flex items-center justify-between rounded-lg border border-white/5 bg-slate-950/40 px-3 py-2">
                        <div>
                          <div className="text-sm font-semibold text-white">{client.name}</div>
                          <div className="text-[10px] text-gray-500">Client company for this workspace</div>
                        </div>
                        <span className="text-[10px] uppercase tracking-wider text-emerald-400 font-bold">Ready</span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="glass-panel p-5">
                {showClientManager ? (
                  <form onSubmit={handleCreateClient} className="space-y-4">
                    <div>
                      <h3 className="text-base font-bold text-white">Create Client Company</h3>
                      <p className="text-xs text-gray-400 mt-1">
                        Add the client company before creating projects or client invites.
                      </p>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                        Client Company Name
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="Alpha Corp"
                        value={newClientName}
                        onChange={(e) => setNewClientName(e.target.value)}
                        className="input-field py-2 text-sm"
                      />
                    </div>

                    <div className="flex gap-3">
                      <button type="button" onClick={() => setShowClientManager(false)} className="btn-secondary text-sm flex-1">
                        Cancel
                      </button>
                      <button type="submit" className="btn-primary text-sm flex-1 justify-center">
                        Save Client
                      </button>
                    </div>
                  </form>
                ) : (
                  <div className="flex h-full min-h-[180px] flex-col justify-between">
                    <div>
                      <h3 className="text-base font-bold text-white">Need a new client?</h3>
                      <p className="text-sm text-gray-400 mt-2">
                        Create the company record first so it appears in project assignment and client invite flows.
                      </p>
                    </div>
                    <button onClick={() => setShowClientManager(true)} className="btn-primary text-sm justify-center mt-6">
                      Create Client Company
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {activeMembership?.role === 'agency_admin' && (
              <div className="glass-panel p-5">
                <div className="flex items-center justify-between gap-4 mb-4">
                  <div>
                    <h3 className="text-base font-bold text-white">Client Intake Forms</h3>
                    <p className="text-xs text-gray-400 mt-1">Create public forms that automatically create a client and project.</p>
                  </div>
                  <button
                    onClick={() => setShowIntakeFormCreator((current) => !current)}
                    className="btn-secondary text-xs py-1.5 px-3"
                  >
                    {showIntakeFormCreator ? 'Hide Form' : 'New Form'}
                  </button>
                </div>

                <div className="space-y-2">
                  {intakeForms.length === 0 ? (
                    <div className="text-sm text-gray-500 italic">No intake forms created yet.</div>
                  ) : (
                    intakeForms.map((form) => (
                      <div key={form.id} className="rounded-lg border border-white/5 bg-slate-950/40 p-3">
                        <div className="flex items-center justify-between gap-2">
                          <div>
                            <div className="text-sm font-semibold text-white">{form.title}</div>
                            <div className="text-[10px] text-gray-500 break-all">/intake-forms/public/{form.share_token}</div>
                          </div>
                          <span className={`text-[10px] uppercase tracking-wider font-bold ${form.is_active ? 'text-emerald-400' : 'text-gray-500'}`}>
                            {form.is_active ? 'Active' : 'Paused'}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {showIntakeFormCreator && (
                  <form onSubmit={handleCreateIntakeForm} className="space-y-3 mt-4 border-t border-white/5 pt-4">
                    <div>
                      <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Form Title</label>
                      <input
                        type="text"
                        value={newIntakeTitle}
                        onChange={(e) => setNewIntakeTitle(e.target.value)}
                        className="input-field py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Fields Schema JSON</label>
                      <textarea
                        value={newIntakeFieldsJson}
                        onChange={(e) => setNewIntakeFieldsJson(e.target.value)}
                        className="input-field h-32 text-xs font-mono"
                      />
                    </div>
                    <button type="submit" className="btn-primary text-sm w-full justify-center">Save Form</button>
                  </form>
                )}
              </div>
            )}

            <div className="glass-panel p-5 lg:col-span-2">
              <div className="flex items-center justify-between gap-4 mb-4">
                <div>
                  <h3 className="text-base font-bold text-white">Notifications</h3>
                  <p className="text-xs text-gray-400 mt-1">Automations from tasks, comments, files, and intake submissions land here.</p>
                </div>
                <span className="text-[10px] uppercase tracking-wider text-violet-400 font-bold">
                  {notifications.filter((notification) => !notification.is_read).length} unread
                </span>
              </div>

              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {notifications.length === 0 ? (
                  <div className="text-sm text-gray-500 italic">No notifications yet.</div>
                ) : (
                  notifications.map((notification) => (
                    <div key={notification.id} className={`rounded-lg border p-3 ${notification.is_read ? 'border-white/5 bg-slate-950/35' : 'border-violet-500/20 bg-violet-950/15'}`}>
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-sm font-semibold text-white">{notification.title}</div>
                          <div className="text-xs text-gray-400 mt-1">{notification.message}</div>
                        </div>
                        {!notification.is_read && (
                          <button
                            onClick={async () => {
                              await apiFetch(`/notifications/${notification.id}/read`, { method: 'POST' });
                              await fetchNotifications();
                            }}
                            className="text-[10px] uppercase tracking-wider text-violet-300 hover:text-violet-200 font-bold"
                          >
                            Mark read
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {projects.length === 0 ? (
            <div className="flex flex-col items-center justify-center flex-1 text-center glass-panel p-12">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 text-gray-600 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
              <h2 className="text-xl font-bold mb-2">No projects configured</h2>
              <p className="text-sm text-gray-500 max-w-sm mb-6">
                There are no active projects registered under this agency context.
              </p>
              {activeMembership?.role === 'agency_admin' && (
                <button onClick={openCreateProject} className="btn-primary">
                  Create Project
                </button>
              )}
            </div>
          ) : !selectedProject ? (
            <div className="text-center text-gray-500 italic p-12">Select a project to begin.</div>
          ) : (
            <>
              {/* Project Title Block & Navigation Tabs */}
              <div className="flex flex-col gap-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>

                    <h2 className="text-2xl font-black text-white">{selectedProject.name}</h2>
                    <p className="text-xs text-gray-400 mt-1">
                      {selectedProject.description || 'No description supplied.'}
                    </p>
                  </div>

                  {activeMembership?.role !== 'client_user' && (
                    <div className="flex border-b border-white/5 gap-1">
                      <button
                        onClick={() => setActiveTab('board')}
                        className={`px-4 py-2 text-sm font-semibold border-b-2 cursor-pointer transition-all ${
                          activeTab === 'board'
                            ? 'border-violet-500 text-white'
                            : 'border-transparent text-gray-500 hover:text-gray-300'
                        }`}
                      >
                        Task Board
                      </button>
                      
                      <button
                        onClick={() => setActiveTab('team')}
                        className={`px-4 py-2 text-sm font-semibold border-b-2 cursor-pointer transition-all ${
                          activeTab === 'team'
                            ? 'border-violet-500 text-white'
                            : 'border-transparent text-gray-500 hover:text-gray-300'
                        }`}
                      >
                        Project Members
                      </button>

                      {activeMembership?.role === 'agency_admin' && (
                        <button
                          onClick={() => setActiveTab('invites')}
                          className={`px-4 py-2 text-sm font-semibold border-b-2 cursor-pointer transition-all ${
                            activeTab === 'invites'
                              ? 'border-violet-500 text-white'
                              : 'border-transparent text-gray-500 hover:text-gray-300'
                          }`}
                        >
                          Workspace Invites
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* ----------------------------------------------------
                    PROJECT SUMMARY REPORTING METRICS (DASHBOARD)
                    ---------------------------------------------------- */}
                {metrics && (
                  <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
                    <div className="glass-panel p-4 flex flex-col gap-1">
                      <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Total Tasks</span>
                      <span className="text-xl font-bold">{metrics.total_tasks}</span>
                    </div>
                    <div className="glass-panel p-4 flex flex-col gap-1 border-l-4 border-l-gray-500">
                      <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">To Do</span>
                      <span className="text-xl font-bold">{metrics.todo_tasks}</span>
                    </div>
                    <div className="glass-panel p-4 flex flex-col gap-1 border-l-4 border-l-blue-500">
                      <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">In Progress</span>
                      <span className="text-xl font-bold">{metrics.in_progress_tasks}</span>
                    </div>
                    <div className="glass-panel p-4 flex flex-col gap-1 border-l-4 border-l-amber-500">
                      <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">In Review</span>
                      <span className="text-xl font-bold">{metrics.in_review_tasks}</span>
                    </div>
                    <div className="glass-panel p-4 flex flex-col gap-1 border-l-4 border-l-emerald-500">
                      <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Completed</span>
                      <span className="text-xl font-bold">{metrics.completed_tasks}</span>
                    </div>
                    <div className="glass-panel p-4 flex flex-col gap-1 border-l-4 border-l-indigo-500">
                      <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Logged Hours</span>
                      <span className="text-xl font-bold text-indigo-400">{metrics.total_hours_logged} hrs</span>
                    </div>
                  </div>
                )}
              </div>

              {/* ----------------------------------------------------
                  BOARD TAB CONTENT
                  ---------------------------------------------------- */}
              {activeTab === 'board' && (
                <div className="flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-bold text-white">Board</h3>
                    {activeMembership?.role !== 'client_user' && (
                      <button onClick={() => setShowAddTask(true)} className="btn-primary py-1.5 px-3 text-xs">
                        Add Task
                      </button>
                    )}
                  </div>

                  {/* KANBAN GRID columns */}
                  <div className="kanban-grid">
                    {['todo', 'in_progress', 'in_review', 'completed'].map((colStatus) => {
                      const colTasks = tasks.filter((t) => t.status === colStatus);
                      const displayTitle = 
                        colStatus === 'todo' ? 'To Do' :
                        colStatus === 'in_progress' ? 'In Progress' :
                        colStatus === 'in_review' ? 'In Review' : 'Completed';

                      return (
                        <div key={colStatus} className="kanban-column">
                          <div className="kanban-header">
                            <span className="text-gray-300 font-semibold">{displayTitle}</span>
                            <span className="text-xs bg-slate-900 border border-white/5 rounded-full px-2 py-0.5 font-bold text-gray-400">
                              {colTasks.length}
                            </span>
                          </div>

                          <div className="flex flex-col gap-3 min-h-[300px] overflow-y-auto">
                            {colTasks.map((task) => (
                              <div
                                key={task.id}
                                onClick={() => handleSelectTask(task)}
                                className={`task-card priority-${task.priority}`}
                              >
                                <div className="flex justify-between items-start gap-2">
                                  <h4 className="text-sm font-semibold text-white leading-snug line-clamp-2">
                                    {task.title}
                                  </h4>
                                  {!task.is_client_visible && (
                                    <span className="text-[9px] font-bold text-amber-500/80 uppercase border border-amber-500/20 bg-amber-500/10 px-1 rounded flex items-center gap-0.5 select-none" title="Internal Only">
                                      <svg xmlns="http://www.w3.org/2000/svg" className="h-2 w-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                      </svg>
                                      Internal
                                    </span>
                                  )}
                                </div>

                                <div className="flex items-center justify-between text-[11px] text-gray-500 mt-2">
                                  <span className="truncate">
                                    {task.assignee ? task.assignee.full_name : 'Unassigned'}
                                  </span>
                                  {task.due_date && (
                                    <span>
                                      Due: {new Date(task.due_date).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                                    </span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* ----------------------------------------------------
                  TEAM TAB CONTENT (ONLY FOR STAFF)
                  ---------------------------------------------------- */}
              {activeTab === 'team' && activeMembership?.role !== 'client_user' && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  
                  {/* List of project members */}
                  <div className="lg:col-span-2 glass-panel p-6 flex flex-col gap-4">
                    <h3 className="text-base font-bold text-white">Assigned Project Members</h3>
                    <div className="flex flex-col divide-y divide-white/5">
                      {projectMembers.map((pm) => (
                        <div key={pm.id} className="flex items-center justify-between py-3">
                          <div>
                            <div className="text-sm font-semibold text-white">{pm.user.full_name}</div>
                            <div className="text-xs text-gray-500">{pm.user.email}</div>
                          </div>
                          {activeMembership?.role === 'agency_admin' && (
                            <button
                              onClick={() => handleRemoveProjectMember(pm.user.id)}
                              className="text-xs text-red-400 hover:text-red-300 font-semibold p-1 hover:bg-red-500/10 rounded cursor-pointer transition-all"
                            >
                              Remove
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Add Project Member form */}
                  {activeMembership?.role === 'agency_admin' && (
                    <div className="glass-panel p-6 flex flex-col gap-4">
                      <h3 className="text-base font-bold text-white">Add Team Member</h3>
                      <form onSubmit={handleAddProjectMember} className="space-y-4">
                        <div>
                          <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                            Select Agency Member
                          </label>
                          <select
                            value={newProjMemberId}
                            onChange={(e) => setNewProjMemberId(e.target.value)}
                            required
                            className="bg-slate-900 border border-white/10 rounded-lg w-full p-2.5 text-sm text-white focus:border-violet-500 outline-none"
                          >
                            <option value="">-- Choose Member --</option>
                            {agencyMembers.map((member) => (
                              <option key={member.id} value={member.user.id}>
                                {member.user.full_name} ({member.role})
                              </option>
                            ))}
                          </select>
                        </div>
                        <button type="submit" className="w-full btn-primary justify-center text-sm py-2">
                          Add to Project
                        </button>
                      </form>
                    </div>
                  )}
                </div>
              )}

              {/* ----------------------------------------------------
                  INVITES TAB CONTENT (ONLY FOR AGENCY ADMIN)
                  ---------------------------------------------------- */}
              {activeTab === 'invites' && activeMembership?.role === 'agency_admin' && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  
                  {/* Agency member management */}
                  <div className="lg:col-span-2 glass-panel p-6 flex flex-col gap-4">
                    <h3 className="text-base font-bold text-white">Active Agency Staff & Clients</h3>
                    <div className="flex flex-col divide-y divide-white/5">
                      {agencyMembers.map((member) => (
                        <div key={member.id} className="flex items-center justify-between py-3">
                          <div>
                            <div className="text-sm font-semibold text-white">{member.user.full_name}</div>
                            <div className="text-xs text-gray-500">{member.user.email}</div>
                          </div>
                          
                          <div className="flex items-center gap-3">
                            <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                              member.role === 'agency_admin' ? 'bg-violet-500/10 text-violet-400 border border-violet-500/20' :
                              member.role === 'agency_member' ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' :
                              'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            }`}>
                              {member.role === 'agency_admin' ? 'Admin' :
                               member.role === 'agency_member' ? 'Staff' :
                               `Client: ${clients.find((client) => client.id === member.client_id)?.name || 'Guest'}`}
                            </span>

                            {member.user.id !== user?.id && (
                              <button
                                onClick={() => handleRemoveAgencyMember(member.user.id)}
                                className="text-xs text-red-400 hover:text-red-300 font-semibold p-1 hover:bg-red-500/10 rounded cursor-pointer transition-all"
                              >
                                Remove
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Invite Generator */}
                  <div className="glass-panel p-6 flex flex-col gap-4">
                    <h3 className="text-base font-bold text-white">Generate Invitation Link</h3>
                    <form onSubmit={handleSendInvite} className="space-y-4">
                      <div>
                        <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                          Email Address
                        </label>
                        <input
                          type="email"
                          required
                          placeholder="collaborator@example.com"
                          value={inviteEmail}
                          onChange={(e) => setInviteEmail(e.target.value)}
                          className="input-field py-2 text-sm"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                          Role Scoping
                        </label>
                        <select
                          value={inviteRole}
                          onChange={(e) => setInviteRole(e.target.value)}
                          className="bg-slate-900 border border-white/10 rounded-lg w-full p-2 text-sm text-white focus:border-violet-500 outline-none"
                        >
                          <option value="agency_member">Agency Staff (Member)</option>
                          <option value="agency_admin">Agency Co-Owner (Admin)</option>
                          <option value="client_user">Client Portal Guest</option>
                        </select>
                      </div>

                      {inviteRole === 'client_user' && (
                        <div>
                          <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                            Select Client Company
                          </label>
                          <select
                            value={inviteClientId}
                            onChange={(e) => setInviteClientId(e.target.value)}
                            required
                            className="bg-slate-900 border border-white/10 rounded-lg w-full p-2 text-sm text-white focus:border-violet-500 outline-none"
                          >
                            <option value="">-- Choose Client --</option>
                            {clients.map((c) => (
                              <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                          </select>
                        </div>
                      )}

                      <button type="submit" className="w-full btn-primary justify-center text-sm py-2">
                        Create Invite Token
                      </button>
                    </form>

                    {inviteTokenGenerated && (
                      <div className="mt-4 p-3 bg-violet-950/20 border border-violet-500/20 rounded-lg">
                        <span className="text-[10px] font-bold text-violet-400 uppercase tracking-wider">Invitation Link:</span>
                        <div className="text-[11px] text-white select-all break-all bg-slate-950 p-2 rounded border border-white/5 mt-1 font-mono">
                          {window.location.origin}/invite/{inviteTokenGenerated}
                        </div>
                        <p className="text-[10px] text-gray-500 mt-2 leading-snug">
                          Share this link with the invitee. It will authenticate and add them to this workspace.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>

      {/* ----------------------------------------------------
          MODAL: ADD NEW PROJECT
          ---------------------------------------------------- */}
      {showAddProject && (
        <div className="modal-overlay">
          <div className="modal-content p-6">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold text-white">Create Project</h3>
              <button onClick={() => setShowAddProject(false)} className="text-gray-400 hover:text-white cursor-pointer">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Project Name</label>
                <input
                  type="text"
                  required
                  placeholder="Website Redesign"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Description</label>
                <textarea
                  placeholder="Details and objectives of the project..."
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  className="input-field h-24"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Assign to Client Company</label>
                {clients.length === 0 ? (
                  <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-4">
                    <p className="text-sm text-amber-200 font-medium">
                      No client company exists yet for this agency.
                    </p>
                    <p className="text-xs text-amber-100/70 mt-1">
                      Create a client company first, then return here to assign it to the project.
                    </p>
                    <button
                      type="button"
                      onClick={() => {
                        setShowAddProject(false);
                        setShowClientManager(true);
                      }}
                      className="btn-primary text-xs mt-3"
                    >
                      Create Client Company
                    </button>
                  </div>
                ) : (
                  <select
                    value={newProjectClientId}
                    onChange={(e) => setNewProjectClientId(e.target.value)}
                    required
                    className="bg-slate-900 border border-white/10 rounded-lg w-full p-3 text-sm text-white focus:border-violet-500 outline-none"
                  >
                    <option value="">-- Choose Client --</option>
                    {clients.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button type="button" onClick={() => setShowAddProject(false)} className="btn-secondary text-sm">
                  Cancel
                </button>
                <button type="submit" className="btn-primary text-sm">
                  Create Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ----------------------------------------------------
          MODAL: ADD NEW TASK
          ---------------------------------------------------- */}
      {showAddTask && selectedProject && (
        <div className="modal-overlay">
          <div className="modal-content p-6">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold text-white">Create Task</h3>
              <button onClick={() => setShowAddTask(false)} className="text-gray-400 hover:text-white cursor-pointer">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Task Title</label>
                <input
                  type="text"
                  required
                  placeholder="Deploy layout configuration files"
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  className="input-field"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Description</label>
                <textarea
                  placeholder="Specify task scope and deliverables..."
                  value={newTaskDesc}
                  onChange={(e) => setNewTaskDesc(e.target.value)}
                  className="input-field h-20"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Priority</label>
                  <select
                    value={newTaskPriority}
                    onChange={(e) => setNewTaskPriority(e.target.value)}
                    className="bg-slate-900 border border-white/10 rounded-lg w-full p-2.5 text-sm text-white focus:border-violet-500 outline-none"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Due Date</label>
                  <input
                    type="date"
                    value={newTaskDueDate}
                    onChange={(e) => setNewTaskDueDate(e.target.value)}
                    className="input-field p-2 text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Assignee (Agency Staff)</label>
                <select
                  value={newTaskAssignee}
                  onChange={(e) => setNewTaskAssignee(e.target.value)}
                  className="bg-slate-900 border border-white/10 rounded-lg w-full p-2.5 text-sm text-white focus:border-violet-500 outline-none"
                >
                  <option value="">-- Unassigned --</option>
                  {projectMembers.map((m) => (
                    <option key={m.id} value={m.user.id}>
                      {m.user.full_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Client Portal Visibility Toggle */}
              <div className="flex items-center gap-3 p-3 bg-slate-900/60 rounded-xl border border-white/5">
                <input
                  type="checkbox"
                  id="task-client-visible"
                  checked={newTaskClientVisible}
                  onChange={(e) => setNewTaskClientVisible(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-700 bg-slate-800 text-violet-500 focus:ring-violet-500 cursor-pointer"
                />
                <label htmlFor="task-client-visible" className="text-sm text-gray-300 font-semibold cursor-pointer select-none">
                  Make task visible to client portal
                </label>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button type="button" onClick={() => setShowAddTask(false)} className="btn-secondary text-sm">
                  Cancel
                </button>
                <button type="submit" className="btn-primary text-sm">
                  Create Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ----------------------------------------------------
          MODAL: DETAILED TASK INSPECT (BOARD DETAIL CONTROLS)
          ---------------------------------------------------- */}
      {inspectedTask && (
        <div className="modal-overlay">
          <div className="modal-content max-w-4xl p-6">
            
            {/* Header */}
            <div className="flex justify-between items-start gap-4 mb-6 border-b border-white/5 pb-4">
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded ${
                    inspectedTask.priority === 'low' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                    inspectedTask.priority === 'medium' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                    inspectedTask.priority === 'high' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                    'bg-red-500/10 text-red-400 border border-red-500/20'
                  }`}>
                    {inspectedTask.priority} Priority
                  </span>
                  
                  {activeMembership?.role !== 'client_user' && (
                    <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded ${
                      inspectedTask.is_client_visible 
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    }`}>
                      {inspectedTask.is_client_visible ? 'Client Visible' : 'Internal Only'}
                    </span>
                  )}
                </div>
                <h3 className="text-xl font-bold text-white leading-tight">{inspectedTask.title}</h3>
              </div>

              <button onClick={() => setInspectedTask(null)} className="text-gray-400 hover:text-white cursor-pointer">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Layout Grid: Task details vs actions & logs */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Col Left: Description, Comments, and File Uploads */}
              <div className="lg:col-span-2 space-y-6">
                <div>
                  <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Description</h4>
                  <div className="bg-slate-900/60 border border-white/5 rounded-xl p-4 text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">
                    {inspectedTask.description || 'No details provided.'}
                  </div>
                </div>

                {/* ----------------------------------------------------
                    FILE UPLOADS & APPROVAL COMPONENT
                    ---------------------------------------------------- */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider">File Assets</h4>
                  
                  {/* File Upload Selector Panel */}
                  <div className="flex flex-col sm:flex-row items-center gap-3 p-3 bg-slate-900/40 rounded-xl border border-white/5">
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileUpload}
                      className="hidden"
                    />
                    <button
                      type="button"
                      disabled={uploadingFile}
                      onClick={() => fileInputRef.current?.click()}
                      className="btn-secondary text-xs py-1.5 px-3 whitespace-nowrap"
                    >
                      {uploadingFile ? 'Uploading...' : 'Choose File'}
                    </button>

                    {activeMembership?.role !== 'client_user' && (
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          id="file-client-visible"
                          checked={uploadClientVisible}
                          onChange={(e) => setUploadClientVisible(e.target.checked)}
                          className="h-3 w-3 rounded text-violet-500 border-slate-700 bg-slate-800"
                        />
                        <label htmlFor="file-client-visible" className="text-xs text-gray-400 select-none cursor-pointer">
                          Client Visible Attachment
                        </label>
                      </div>
                    )}
                  </div>

                  {/* File attachments list */}
                  <div className="flex flex-col gap-2">
                    {taskFiles.length === 0 ? (
                      <div className="text-xs text-gray-600 italic">No files attached to task.</div>
                    ) : (
                      taskFiles.map((file) => (
                        <div key={file.id} className="flex items-center justify-between p-3 bg-slate-900/60 border border-white/5 rounded-xl">
                          <div className="flex flex-col min-w-0">
                            <span className="text-xs font-semibold text-white truncate max-w-[280px]">{file.filename}</span>
                            <span className="text-[10px] text-gray-500">
                              Uploaded by: {file.uploader.full_name} • {(file.file_size / 1024).toFixed(1)} KB
                            </span>
                          </div>

                          <div className="flex items-center gap-3">
                            {/* Download Icon */}
                            <a
                              href={`${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/files/${file.id}/download?token=${localStorage.getItem('token')}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-1 rounded bg-slate-900 border border-white/5 text-gray-400 hover:text-white"
                              title="Download Attachment"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                              </svg>
                            </a>

                            {/* Approval Status Badge */}
                            <span className={`text-[9px] px-2 py-0.5 rounded font-bold uppercase ${
                              file.approval_status === 'approved' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                              file.approval_status === 'changes_requested' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                              'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                            }`}>
                              {file.approval_status === 'changes_requested' ? 'Needs Changes' : file.approval_status}
                            </span>

                            {/* Client Approval Switches */}
                            {activeMembership?.role === 'client_user' && (
                              <div className="flex gap-1">
                                <button
                                  onClick={() => handleFileApproval(file.id, 'approved')}
                                  className="px-2 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-[10px] font-bold cursor-pointer"
                                >
                                  Approve
                                </button>
                                <button
                                  onClick={() => handleFileApproval(file.id, 'changes_requested')}
                                  className="px-2 py-1 bg-red-600 hover:bg-red-500 text-white rounded text-[10px] font-bold cursor-pointer"
                                >
                                  Reject
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* ----------------------------------------------------
                    TASK COMMENTS BOARD
                    ---------------------------------------------------- */}
                <div className="space-y-4">
                  <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Discussion Board</h4>
                  
                  {/* Comments feed */}
                  <div className="flex flex-col gap-3 max-h-60 overflow-y-auto">
                    {taskComments.length === 0 ? (
                      <div className="text-xs text-gray-600 italic">No comments posted yet.</div>
                    ) : (
                      taskComments.map((comm) => (
                        <div key={comm.id} className="p-3 bg-slate-900/40 border border-white/5 rounded-xl space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-white">{comm.author.full_name}</span>
                            <div className="flex items-center gap-2">
                              {!comm.is_client_visible && (
                                <span className="text-[9px] font-bold text-amber-500 bg-amber-500/10 border border-amber-500/20 px-1 rounded">
                                  Internal Note
                                </span>
                              )}
                              <span className="text-[10px] text-gray-500">
                                {new Date(comm.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>
                          </div>
                          <p className="text-xs text-gray-300 leading-normal">{comm.content}</p>
                        </div>
                      ))
                    )}
                  </div>

                  {/* Add comment form */}
                  <form onSubmit={handleCreateComment} className="space-y-3">
                    <textarea
                      required
                      placeholder="Type your message here..."
                      value={newCommentText}
                      onChange={(e) => setNewCommentText(e.target.value)}
                      className="input-field h-16 text-xs p-3"
                    />

                    <div className="flex items-center justify-between">
                      {activeMembership?.role !== 'client_user' ? (
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            id="comm-client-visible"
                            checked={newCommentClientVisible}
                            onChange={(e) => setNewCommentClientVisible(e.target.checked)}
                            className="h-3.5 w-3.5 rounded text-violet-500 border-slate-700 bg-slate-800"
                          />
                          <label htmlFor="comm-client-visible" className="text-xs text-gray-400 select-none cursor-pointer">
                            Visible to Client Portal
                          </label>
                        </div>
                      ) : (
                        <span className="text-[10px] text-gray-500 font-semibold uppercase">
                          Posting to portal (Client-visible)
                        </span>
                      )}

                      <button type="submit" className="btn-primary text-xs py-1.5 px-3">
                        Post Comment
                      </button>
                    </div>
                  </form>
                </div>
              </div>

              {/* Col Right: Task status selectors & hours logger */}
              <div className="space-y-6">
                
                {/* Status Update Panel */}
                <div>
                  <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Task Operations</h4>
                  {activeMembership?.role === 'client_user' ? (
                    <div className="p-3 bg-slate-900/60 border border-white/5 rounded-xl">
                      <span className="text-xs text-gray-400">Current Status:</span>
                      <div className="text-sm font-extrabold text-white mt-1 capitalize">{inspectedTask.status.replace('_', ' ')}</div>
                      <p className="text-[10px] text-gray-500 mt-2">
                        Clients cannot modify task statuses. Please contact the agency manager.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider">Update Status</label>
                      <select
                        value={inspectedTask.status}
                        onChange={(e) => handleUpdateTaskStatus(inspectedTask.id, e.target.value)}
                        className="bg-slate-900 border border-white/10 rounded-lg w-full p-2.5 text-sm text-white focus:border-violet-500 outline-none"
                      >
                        <option value="todo">To Do</option>
                        <option value="in_progress">In Progress</option>
                        <option value="in_review">In Review</option>
                        <option value="completed">Completed</option>
                      </select>
                    </div>
                  )}
                </div>

                {/* Task attributes review */}
                <div className="p-4 bg-slate-900/40 border border-white/5 rounded-xl space-y-3 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Assignee:</span>
                    <span className="font-bold text-white">{inspectedTask.assignee ? inspectedTask.assignee.full_name : 'Unassigned'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Due Date:</span>
                    <span className="font-bold text-white">
                      {inspectedTask.due_date ? new Date(inspectedTask.due_date).toLocaleDateString() : 'No date set'}
                    </span>
                  </div>
                </div>

                {/* ----------------------------------------------------
                    TIME LOGGING (INTERNAL ONLY)
                    ---------------------------------------------------- */}
                {activeMembership?.role !== 'client_user' && (
                  <div className="space-y-4">
                    <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Log Time</h4>
                    
                    {/* Time entries list */}
                    <div className="flex flex-col gap-2 max-h-40 overflow-y-auto">
                      {taskTimeEntries.length === 0 ? (
                        <div className="text-xs text-gray-600 italic">No hours logged against task.</div>
                      ) : (
                        taskTimeEntries.map((te) => (
                          <div key={te.id} className="p-2 bg-slate-900/60 border border-white/5 rounded-lg flex items-center justify-between text-xs">
                            <div className="flex flex-col">
                              <span className="font-bold text-white">{formatDuration(te.duration_minutes)}</span>
                              <span className="text-[10px] text-gray-500">{te.note || 'General works'}</span>
                            </div>
                            <span className="text-[9px] text-gray-500">{te.date}</span>
                          </div>
                        ))
                      )}
                    </div>

                    {/* Add time logger form */}
                    <form onSubmit={handleLogTime} className="space-y-3 p-3 bg-slate-900/40 border border-white/5 rounded-xl">
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Minutes</label>
                          <input
                            type="number"
                            required
                            min={1}
                            value={newTimeMinutes}
                            onChange={(e) => setNewTimeMinutes(Number(e.target.value))}
                            className="input-field py-1.5 px-2 text-xs"
                          />
                        </div>
                        <div className="flex flex-col justify-end">
                          <span className="text-[10px] text-gray-500 font-semibold text-center mb-2">
                            = {roundHours(newTimeMinutes)} hrs
                          </span>
                        </div>
                      </div>

                      <div>
                        <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Note</label>
                        <input
                          type="text"
                          placeholder="e.g. Iterating mockup screens"
                          value={newTimeNote}
                          onChange={(e) => setNewTimeNote(e.target.value)}
                          className="input-field py-1.5 px-2 text-xs"
                        />
                      </div>

                      <button type="submit" className="w-full btn-primary justify-center text-xs py-1.5">
                        Log Entry
                      </button>
                    </form>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function roundHours(mins: number) {
  return round(mins / 60.0, 2);
}

function round(value: number, precision: number) {
  const multiplier = Math.pow(10, precision || 0);
  return Math.round(value * multiplier) / multiplier;
}
