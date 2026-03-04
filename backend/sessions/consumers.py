"""
WebSocket consumers for real-time concurrent editing.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Student, Employee
from compliance.utils import log_access

User = get_user_model()


class StudentEditConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for student editing with optimistic locking."""
    
    async def connect(self):
        self.student_id = self.scope['url_route']['kwargs']['student_id']
        self.room_group_name = f'student_{self.student_id}'
        self.user = self.scope['user']
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Lock the student record
        await self.lock_student()
        
        # Notify others that user is editing
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': self.user.id,
                'user_email': self.user.email,
                'message': f'{self.user.email} started editing'
            }
        )
    
    async def disconnect(self, close_code):
        # Unlock the student record
        await self.unlock_student()
        
        # Notify others that user left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': self.user.id,
                'user_email': self.user.email,
                'message': f'{self.user.email} stopped editing'
            }
        )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Receive message from WebSocket."""
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'edit':
            # Handle edit operation
            await self.handle_edit(data)
        elif message_type == 'ping':
            # Keep-alive ping
            await self.send(text_data=json.dumps({'type': 'pong'}))
    
    async def handle_edit(self, data):
        """Handle edit operation with optimistic locking."""
        try:
            student = await self.get_student()
            if not student:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Student not found'
                }))
                return
            
            # Check version for optimistic locking
            expected_version = data.get('version')
            if student.version != expected_version:
                await self.send(text_data=json.dumps({
                    'type': 'conflict',
                    'message': 'Record was modified by another user',
                    'current_version': student.version,
                    'server_data': await self.get_student_data(student)
                }))
                return
            
            # Update student
            await self.update_student(student, data.get('changes', {}))
            
            # Broadcast update to all users in room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'record_updated',
                    'user_id': self.user.id,
                    'user_email': self.user.email,
                    'changes': data.get('changes', {}),
                    'version': student.version
                }
            )
            
            # Log access
            await self.log_access('update', data.get('changes', {}))
            
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def user_joined(self, event):
        """Send message when user joins."""
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user_email': event['user_email'],
            'message': event['message']
        }))
    
    async def user_left(self, event):
        """Send message when user leaves."""
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user_email': event['user_email'],
            'message': event['message']
        }))
    
    async def record_updated(self, event):
        """Send message when record is updated."""
        await self.send(text_data=json.dumps({
            'type': 'record_updated',
            'user_email': event['user_email'],
            'changes': event['changes'],
            'version': event['version']
        }))
    
    @database_sync_to_async
    def get_student(self):
        """Get student from database."""
        try:
            return Student.objects.get(id=self.student_id)
        except Student.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_student_data(self, student):
        """Get student data as dict."""
        from .serializers import StudentSerializer
        serializer = StudentSerializer(student)
        return serializer.data
    
    @database_sync_to_async
    def lock_student(self):
        """Lock student record."""
        try:
            student = Student.objects.get(id=self.student_id)
            if student.locked_by and student.locked_by != self.user:
                # Already locked by someone else
                return False
            student.locked_by = self.user
            student.locked_at = timezone.now()
            student.save()
            return True
        except Student.DoesNotExist:
            return False
    
    @database_sync_to_async
    def unlock_student(self):
        """Unlock student record."""
        try:
            student = Student.objects.get(id=self.student_id)
            if student.locked_by == self.user:
                student.locked_by = None
                student.locked_at = None
                student.save()
        except Student.DoesNotExist:
            pass
    
    @database_sync_to_async
    def update_student(self, student, changes):
        """Update student with changes."""
        for field, value in changes.items():
            if hasattr(student, field):
                setattr(student, field, value)
        student.version += 1
        student.save()
    
    @database_sync_to_async
    def log_access(self, action, changes):
        """Log access for audit."""
        try:
            log_access(
                self.user,
                'student',
                self.student_id,
                action,
                None,  # request not available in async context
                changes
            )
        except Exception:
            pass


class EmployeeEditConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for employee editing with optimistic locking."""
    
    async def connect(self):
        self.employee_id = self.scope['url_route']['kwargs']['employee_id']
        self.room_group_name = f'employee_{self.employee_id}'
        self.user = self.scope['user']
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Lock the employee record
        await self.lock_employee()
        
        # Notify others that user is editing
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': self.user.id,
                'user_email': self.user.email,
                'message': f'{self.user.email} started editing'
            }
        )
    
    async def disconnect(self, close_code):
        # Unlock the employee record
        await self.unlock_employee()
        
        # Notify others that user left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': self.user.id,
                'user_email': self.user.email,
                'message': f'{self.user.email} stopped editing'
            }
        )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Receive message from WebSocket."""
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'edit':
            await self.handle_edit(data)
        elif message_type == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
    
    async def handle_edit(self, data):
        """Handle edit operation with optimistic locking."""
        try:
            employee = await self.get_employee()
            if not employee:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Employee not found'
                }))
                return
            
            # Check version for optimistic locking
            expected_version = data.get('version')
            if employee.version != expected_version:
                await self.send(text_data=json.dumps({
                    'type': 'conflict',
                    'message': 'Record was modified by another user',
                    'current_version': employee.version,
                    'server_data': await self.get_employee_data(employee)
                }))
                return
            
            # Update employee
            await self.update_employee(employee, data.get('changes', {}))
            
            # Broadcast update to all users in room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'record_updated',
                    'user_id': self.user.id,
                    'user_email': self.user.email,
                    'changes': data.get('changes', {}),
                    'version': employee.version
                }
            )
            
            # Log access
            await self.log_access('update', data.get('changes', {}))
            
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def user_joined(self, event):
        """Send message when user joins."""
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user_email': event['user_email'],
            'message': event['message']
        }))
    
    async def user_left(self, event):
        """Send message when user leaves."""
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user_email': event['user_email'],
            'message': event['message']
        }))
    
    async def record_updated(self, event):
        """Send message when record is updated."""
        await self.send(text_data=json.dumps({
            'type': 'record_updated',
            'user_email': event['user_email'],
            'changes': event['changes'],
            'version': event['version']
        }))
    
    @database_sync_to_async
    def get_employee(self):
        """Get employee from database."""
        try:
            return Employee.objects.get(id=self.employee_id)
        except Employee.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_employee_data(self, employee):
        """Get employee data as dict."""
        from .serializers import EmployeeSerializer
        serializer = EmployeeSerializer(employee)
        return serializer.data
    
    @database_sync_to_async
    def lock_employee(self):
        """Lock employee record."""
        try:
            employee = Employee.objects.get(id=self.employee_id)
            if employee.locked_by and employee.locked_by != self.user:
                return False
            employee.locked_by = self.user
            employee.locked_at = timezone.now()
            employee.save()
            return True
        except Employee.DoesNotExist:
            return False
    
    @database_sync_to_async
    def unlock_employee(self):
        """Unlock employee record."""
        try:
            employee = Employee.objects.get(id=self.employee_id)
            if employee.locked_by == self.user:
                employee.locked_by = None
                employee.locked_at = None
                employee.save()
        except Employee.DoesNotExist:
            pass
    
    @database_sync_to_async
    def update_employee(self, employee, changes):
        """Update employee with changes."""
        for field, value in changes.items():
            if hasattr(employee, field):
                setattr(employee, field, value)
        employee.version += 1
        employee.save()
    
    @database_sync_to_async
    def log_access(self, action, changes):
        """Log access for audit."""
        try:
            log_access(
                self.user,
                'employee',
                self.employee_id,
                action,
                None,
                changes
            )
        except Exception:
            pass


class SessionConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for session-level updates."""
    
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'session_{self.session_id}'
        self.user = self.scope['user']
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Receive message from WebSocket."""
        data = json.loads(text_data)
        # Handle session-level messages if needed
        pass
    
    async def session_update(self, event):
        """Send session update message."""
        await self.send(text_data=json.dumps({
            'type': 'session_update',
            'data': event['data']
        }))
