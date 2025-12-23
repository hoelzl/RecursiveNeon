"""
Task Service

Manages task lists and tasks with CRUD operations.
"""
import uuid
from typing import Dict, Any, List

from recursive_neon.models.app_models import Task, TaskList, TasksState


class TaskService:
    """
    Service for managing tasks and task lists.

    Provides CRUD operations for the task management application.
    """

    def __init__(self, tasks_state: TasksState):
        """
        Initialize the task service.

        Args:
            tasks_state: The tasks state to manage
        """
        self._state = tasks_state

    # ============================================================================
    # Task List Operations
    # ============================================================================

    def get_lists(self) -> List[TaskList]:
        """Get all task lists."""
        return self._state.lists

    def get_list(self, list_id: str) -> TaskList:
        """
        Get a specific task list by ID.

        Args:
            list_id: ID of the task list

        Returns:
            The task list

        Raises:
            ValueError: If task list not found
        """
        for task_list in self._state.lists:
            if task_list.id == list_id:
                return task_list
        raise ValueError(f"Task list not found: {list_id}")

    def create_list(self, data: Dict[str, Any]) -> TaskList:
        """
        Create a new task list.

        Args:
            data: Task list data (name)

        Returns:
            The created task list
        """
        task_list = TaskList(
            id=str(uuid.uuid4()),
            name=data.get("name", "Untitled List"),
            tasks=[],
        )
        self._state.lists.append(task_list)
        return task_list

    def update_list(self, list_id: str, data: Dict[str, Any]) -> TaskList:
        """
        Update a task list.

        Args:
            list_id: ID of the task list
            data: Updated data

        Returns:
            The updated task list

        Raises:
            ValueError: If task list not found
        """
        task_list = self.get_list(list_id)
        for i, tl in enumerate(self._state.lists):
            if tl.id == list_id:
                updated = TaskList(
                    id=task_list.id,
                    name=data.get("name", task_list.name),
                    tasks=task_list.tasks,
                )
                self._state.lists[i] = updated
                return updated
        raise ValueError(f"Task list not found: {list_id}")

    def delete_list(self, list_id: str) -> None:
        """
        Delete a task list.

        Args:
            list_id: ID of the task list to delete
        """
        self._state.lists = [
            tl for tl in self._state.lists if tl.id != list_id
        ]

    # ============================================================================
    # Task Operations
    # ============================================================================

    def create_task(self, list_id: str, data: Dict[str, Any]) -> Task:
        """
        Create a new task in a list.

        Args:
            list_id: ID of the task list
            data: Task data (title, completed, parent_id)

        Returns:
            The created task
        """
        self.get_list(list_id)  # Verify list exists
        task = Task(
            id=str(uuid.uuid4()),
            title=data.get("title", "Untitled Task"),
            completed=data.get("completed", False),
            parent_id=data.get("parent_id"),
        )

        for i, tl in enumerate(self._state.lists):
            if tl.id == list_id:
                updated_tasks = list(tl.tasks)
                updated_tasks.append(task)
                self._state.lists[i] = TaskList(
                    id=tl.id,
                    name=tl.name,
                    tasks=updated_tasks,
                )
                break

        return task

    def update_task(self, list_id: str, task_id: str, data: Dict[str, Any]) -> Task:
        """
        Update a task.

        Args:
            list_id: ID of the task list
            task_id: ID of the task
            data: Updated task data

        Returns:
            The updated task

        Raises:
            ValueError: If task not found
        """
        self.get_list(list_id)  # Verify list exists

        for i, tl in enumerate(self._state.lists):
            if tl.id == list_id:
                updated_tasks = []
                updated_task = None
                for task in tl.tasks:
                    if task.id == task_id:
                        updated_task = Task(
                            id=task.id,
                            title=data.get("title", task.title),
                            completed=data.get("completed", task.completed),
                            parent_id=data.get("parent_id", task.parent_id),
                        )
                        updated_tasks.append(updated_task)
                    else:
                        updated_tasks.append(task)

                if updated_task:
                    self._state.lists[i] = TaskList(
                        id=tl.id,
                        name=tl.name,
                        tasks=updated_tasks,
                    )
                    return updated_task

        raise ValueError(f"Task not found: {task_id}")

    def delete_task(self, list_id: str, task_id: str) -> None:
        """
        Delete a task.

        Args:
            list_id: ID of the task list
            task_id: ID of the task to delete
        """
        self.get_list(list_id)  # Verify list exists

        for i, tl in enumerate(self._state.lists):
            if tl.id == list_id:
                self._state.lists[i] = TaskList(
                    id=tl.id,
                    name=tl.name,
                    tasks=[t for t in tl.tasks if t.id != task_id],
                )
                break
