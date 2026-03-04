/**
 * WebSocket service for real-time concurrent editing.
 */
class WebSocketService {
  constructor() {
    this.connections = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  /**
   * Connect to WebSocket for student editing.
   */
  connectStudent(studentId, token, callbacks) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = process.env.REACT_APP_WS_URL || window.location.host.replace(':3000', ':8000');
    const url = `${wsProtocol}//${wsHost}/ws/students/${studentId}/`;

    return this.connect(url, token, callbacks, `student_${studentId}`);
  }

  /**
   * Connect to WebSocket for employee editing.
   */
  connectEmployee(employeeId, token, callbacks) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = process.env.REACT_APP_WS_URL || window.location.host.replace(':3000', ':8000');
    const url = `${wsProtocol}//${wsHost}/ws/employees/${employeeId}/`;

    return this.connect(url, token, callbacks, `employee_${employeeId}`);
  }

  /**
   * Connect to WebSocket.
   */
  connect(url, token, callbacks, key) {
    // Close existing connection if any
    if (this.connections.has(key)) {
      this.connections.get(key).close();
    }

    const ws = new WebSocket(`${url}?token=${token}`);

    ws.onopen = () => {
      console.log(`WebSocket connected: ${key}`);
      this.reconnectAttempts = 0;
      
      // Send ping every 30 seconds to keep connection alive
      this.pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000);

      if (callbacks.onOpen) callbacks.onOpen();
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'user_joined':
          if (callbacks.onUserJoined) callbacks.onUserJoined(data);
          break;
        case 'user_left':
          if (callbacks.onUserLeft) callbacks.onUserLeft(data);
          break;
        case 'record_updated':
          if (callbacks.onRecordUpdated) callbacks.onRecordUpdated(data);
          break;
        case 'conflict':
          if (callbacks.onConflict) callbacks.onConflict(data);
          break;
        case 'error':
          if (callbacks.onError) callbacks.onError(data);
          break;
        case 'pong':
          // Keep-alive response
          break;
        default:
          console.log('Unknown message type:', data.type);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (callbacks.onError) callbacks.onError({ message: 'WebSocket connection error' });
    };

    ws.onclose = () => {
      console.log(`WebSocket disconnected: ${key}`);
      if (this.pingInterval) {
        clearInterval(this.pingInterval);
      }

      // Attempt to reconnect
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        setTimeout(() => {
          console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`);
          this.connect(url, token, callbacks, key);
        }, 1000 * this.reconnectAttempts);
      } else {
        if (callbacks.onClose) callbacks.onClose();
      }
    };

    this.connections.set(key, ws);
    return ws;
  }

  /**
   * Send edit message.
   */
  sendEdit(key, changes, version) {
    const ws = this.connections.get(key);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'edit',
        changes,
        version
      }));
    } else {
      console.error('WebSocket not connected');
    }
  }

  /**
   * Disconnect WebSocket.
   */
  disconnect(key) {
    const ws = this.connections.get(key);
    if (ws) {
      ws.close();
      this.connections.delete(key);
    }
  }

  /**
   * Disconnect all connections.
   */
  disconnectAll() {
    this.connections.forEach((ws, key) => {
      ws.close();
    });
    this.connections.clear();
  }
}

export default new WebSocketService();
