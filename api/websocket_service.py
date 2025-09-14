"""
WebSocket service helper functions for easy broadcasting
"""

from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class WebSocketService:
    """Service class for WebSocket operations"""
    
    @staticmethod
    async def notify_agent_status(
        websocket_manager,
        agent_name: str,
        project_id: str,
        status: str,
        **kwargs
    ):
        """Helper to notify agent status changes"""
        if not websocket_manager:
            return
            
        try:
            await websocket_manager.broadcast_agent_update(
                agent_name=agent_name,
                project_id=project_id,
                status=status,
                additional_data=kwargs
            )
        except Exception as e:
            logger.error(f"Failed to broadcast agent status: {e}")
    
    @staticmethod
    async def notify_message(
        websocket_manager,
        message_id: str,
        project_id: str,
        update_type: str,
        **kwargs
    ):
        """Helper to notify message updates"""
        if not websocket_manager:
            return
            
        try:
            await websocket_manager.broadcast_message_update(
                message_id=message_id,
                project_id=project_id,
                update_type=update_type,
                message_data=kwargs
            )
        except Exception as e:
            logger.error(f"Failed to broadcast message update: {e}")
    
    @staticmethod
    async def notify_progress(
        websocket_manager,
        operation_id: str,
        project_id: str,
        percentage: float,
        message: str,
        **kwargs
    ):
        """Helper to notify progress updates"""
        if not websocket_manager:
            return
            
        try:
            await websocket_manager.broadcast_progress(
                operation_id=operation_id,
                project_id=project_id,
                percentage=percentage,
                message=message,
                details=kwargs
            )
        except Exception as e:
            logger.error(f"Failed to broadcast progress: {e}")
    
    @staticmethod
    async def notify_project(
        websocket_manager,
        project_id: str,
        update_type: str,
        **kwargs
    ):
        """Helper to notify project updates"""
        if not websocket_manager:
            return
            
        try:
            await websocket_manager.broadcast_project_update(
                project_id=project_id,
                update_type=update_type,
                project_data=kwargs
            )
        except Exception as e:
            logger.error(f"Failed to broadcast project update: {e}")
    
    @staticmethod
    async def send_notification(
        websocket_manager,
        notification_type: str,
        title: str,
        message: str,
        project_id: Optional[str] = None,
        target_clients: Optional[List[str]] = None
    ):
        """Helper to send notifications"""
        if not websocket_manager:
            return
            
        try:
            await websocket_manager.broadcast_notification(
                notification_type=notification_type,
                title=title,
                message=message,
                project_id=project_id,
                target_clients=target_clients
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    @staticmethod
    async def notify_long_operation_start(
        websocket_manager,
        operation_id: str,
        project_id: str,
        operation_name: str,
        estimated_duration: Optional[int] = None
    ):
        """Notify start of a long-running operation"""
        if not websocket_manager:
            return
            
        await WebSocketService.notify_progress(
            websocket_manager,
            operation_id=operation_id,
            project_id=project_id,
            percentage=0,
            message=f"Starting {operation_name}",
            operation_name=operation_name,
            estimated_duration=estimated_duration
        )
    
    @staticmethod
    async def notify_long_operation_progress(
        websocket_manager,
        operation_id: str,
        project_id: str,
        percentage: float,
        current_step: str,
        steps_completed: Optional[int] = None,
        total_steps: Optional[int] = None
    ):
        """Notify progress of a long-running operation"""
        if not websocket_manager:
            return
            
        await WebSocketService.notify_progress(
            websocket_manager,
            operation_id=operation_id,
            project_id=project_id,
            percentage=percentage,
            message=current_step,
            steps_completed=steps_completed,
            total_steps=total_steps
        )
    
    @staticmethod
    async def notify_long_operation_complete(
        websocket_manager,
        operation_id: str,
        project_id: str,
        operation_name: str,
        success: bool = True,
        result: Optional[str] = None
    ):
        """Notify completion of a long-running operation"""
        if not websocket_manager:
            return
            
        message = f"{operation_name} completed successfully" if success else f"{operation_name} failed"
        
        await WebSocketService.notify_progress(
            websocket_manager,
            operation_id=operation_id,
            project_id=project_id,
            percentage=100 if success else -1,
            message=message,
            success=success,
            result=result
        )
        
        # Also send a notification
        notification_type = "success" if success else "error"
        await WebSocketService.send_notification(
            websocket_manager,
            notification_type=notification_type,
            title=operation_name,
            message=message,
            project_id=project_id
        )
    
    @staticmethod
    def get_connection_stats(websocket_manager) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        if not websocket_manager:
            return {
                "active_connections": 0,
                "total_subscriptions": 0,
                "status": "unavailable"
            }
        
        return {
            "active_connections": websocket_manager.get_connection_count(),
            "total_subscriptions": websocket_manager.get_subscription_count(),
            "status": "operational"
        }