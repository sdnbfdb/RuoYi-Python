const API_BASE_URL = 'http://localhost:5000/api';

const Api = {
  auth: {
    login: async (account, password) => {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ account, password }),
      });
      return response.json();
    },

    register: async (account, password, confirmPassword) => {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ account, password, confirmPassword }),
      });
      return response.json();
    },

    logout: async () => {
      const response = await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
      return response.json();
    },

    getProfile: async () => {
      const response = await fetch(`${API_BASE_URL}/auth/profile`, {
        method: 'GET',
        credentials: 'include',
      });
      return response.json();
    },

    updateProfile: async (userData) => {
      const response = await fetch(`${API_BASE_URL}/auth/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(userData),
      });
      return response.json();
    },
  },

  agent: {
    getAgents: async () => {
      const response = await fetch(`${API_BASE_URL}/agents`, {
        method: 'GET',
        credentials: 'include',
      });
      return response.json();
    },

    getAgentById: async (agentId) => {
      const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, {
        method: 'GET',
        credentials: 'include',
      });
      return response.json();
    },

    createAgent: async (agentData) => {
      const response = await fetch(`${API_BASE_URL}/agents`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(agentData),
      });
      return response.json();
    },

    updateAgent: async (agentId, agentData) => {
      const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(agentData),
      });
      return response.json();
    },

    deleteAgent: async (agentId) => {
      const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      return response.json();
    },

    sendMessage: async (agentId, message) => {
      const response = await fetch(`${API_BASE_URL}/agents/${agentId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ message }),
      });
      return response.json();
    },

    generateImage: async (prompt) => {
      const response = await fetch(`${API_BASE_URL}/agents/image/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ prompt }),
      });
      return response.json();
    },

    writeContent: async (topic) => {
      const response = await fetch(`${API_BASE_URL}/agents/write`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ topic }),
      });
      return response.json();
    },

    translate: async (text, targetLang) => {
      const response = await fetch(`${API_BASE_URL}/agents/translate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ text, targetLang }),
      });
      return response.json();
    },
  },

  operations: {
    getOperations: async (params = {}) => {
      const queryString = new URLSearchParams(params).toString();
      const response = await fetch(`${API_BASE_URL}/operations?${queryString}`, {
        method: 'GET',
        credentials: 'include',
      });
      return response.json();
    },

    getOperationById: async (operationId) => {
      const response = await fetch(`${API_BASE_URL}/operations/${operationId}`, {
        method: 'GET',
        credentials: 'include',
      });
      return response.json();
    },

    createOperation: async (operationData) => {
      const response = await fetch(`${API_BASE_URL}/operations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(operationData),
      });
      return response.json();
    },

    updateOperation: async (operationId, operationData) => {
      const response = await fetch(`${API_BASE_URL}/operations/${operationId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(operationData),
      });
      return response.json();
    },

    deleteOperation: async (operationId) => {
      const response = await fetch(`${API_BASE_URL}/operations/${operationId}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      return response.json();
    },

    exportOperation: async (operationId) => {
      const response = await fetch(`${API_BASE_URL}/operations/${operationId}/export`, {
        method: 'GET',
        credentials: 'include',
      });
      return response.blob();
    },
  },

  users: {
    getUsers: async (params = {}) => {
      const queryString = new URLSearchParams(params).toString();
      const response = await fetch(`${API_BASE_URL}/users?${queryString}`, {
        method: 'GET',
        credentials: 'include',
      });
      return response.json();
    },

    getUserById: async (userId) => {
      const response = await fetch(`${API_BASE_URL}/users/${userId}`, {
        method: 'GET',
        credentials: 'include',
      });
      return response.json();
    },

    createUser: async (userData) => {
      const response = await fetch(`${API_BASE_URL}/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(userData),
      });
      return response.json();
    },

    updateUser: async (userId, userData) => {
      const response = await fetch(`${API_BASE_URL}/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(userData),
      });
      return response.json();
    },

    deleteUser: async (userId) => {
      const response = await fetch(`${API_BASE_URL}/users/${userId}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      return response.json();
    },
  },

  upload: {
    uploadFile: async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });
      return response.json();
    },

    uploadFiles: async (files) => {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append('files', file);
      });
      
      const response = await fetch(`${API_BASE_URL}/upload/batch`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });
      return response.json();
    },
  },
};

export default Api;
