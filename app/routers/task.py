from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app import enums

from ..database import get_db
from .. import schemas, models, utils, oauth2
from ..error import add_error

router = APIRouter(
    prefix="/task",
    tags=["task"]
)

@router.post("/", response_model=schemas.taskOut)
def add(task: schemas.taskIn, db: Session = Depends(get_db), current_user=Depends(oauth2.get_current_user)):
    """Create a new task"""
    try:
        task_dict = task.model_dump() 
        task_dict["user_id"] = current_user.id
        new_task = models.Task(**task_dict)  
        db.add(new_task)
        db.commit()
        db.refresh(new_task)

    except Exception as e:
        db.rollback()
        add_error(e, db)
        print(e)
        return schemas.taskOut(
            status=status.HTTP_400_BAD_REQUEST,
            message="Failed to add task"
        )

    return schemas.taskOut(
        **new_task.__dict__,
        status=status.HTTP_201_CREATED,
        message="Task added successfully"
    )

@router.get("/", response_model=schemas.tasksOut)
def get_all(
    page_size: int = Query(10, ge=1, le=100),
    page_number: int = Query(1, ge=1),
    state: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query("created_on", pattern="^(created_on|due_date|title|state)$"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    """
    Get all tasks with filtering, search, sorting, and pagination
    
    - **state**: Filter by state (todo, doing, done)
    - **tag**: Filter by tag (optional, important, urgent)
    - **search**: Search in title and description
    - **sort_by**: Sort by field (created_on, due_date, title, state)
    - **sort_order**: Sort order (asc, desc)
    """
    try:
        query = db.query(models.Task).filter(models.Task.user_id == current_user.id)

        if state:
            try:
                state_enum = enums.State[state]
                query = query.filter(models.Task.state == state_enum)
            except KeyError:
                return schemas.tasksOut(
                    list=[],
                    total_pages=0,
                    total_records=0,
                    page_number=page_number,
                    page_size=page_size,
                    status=status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid state: {state}"
                )
        if tag:
            try:
                tag_enum = enums.Tag[tag]
                query = query.filter(models.Task.tag == tag_enum)
            except KeyError:
                return schemas.tasksOut(
                    list=[],
                    total_pages=0,
                    total_records=0,
                    page_number=page_number,
                    page_size=page_size,
                    status=status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid tag: {tag}"
                )

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (models.Task.title.ilike(search_term)) | 
                (models.Task.description.ilike(search_term))
            )

        if sort_by == "created_on":
            order_column = models.Task.created_on
        elif sort_by == "due_date":
            order_column = models.Task.due_date
        elif sort_by == "title":
            order_column = models.Task.title
        elif sort_by == "state":
            order_column = models.Task.state
        else:
            order_column = models.Task.created_on

        if sort_order == "asc":
            query = query.order_by(order_column.asc())
        else:
            query = query.order_by(order_column.desc())


        total_records = query.count()
        total_pages = utils.div_ceil(total_records, page_size)

        tasks = (
            query
            .limit(page_size)
            .offset((page_number - 1) * page_size)
            .all()
        )

    except Exception as e:
        add_error(e, db)
        return schemas.tasksOut(
            list=[],
            total_pages=0,
            total_records=0,
            page_number=page_number,
            page_size=page_size,
            status=status.HTTP_400_BAD_REQUEST,
            message="Failed to retrieve tasks"
        )

    return schemas.tasksOut(
        total_pages=total_pages,
        total_records=total_records,
        page_number=page_number,
        page_size=page_size,
        list=[schemas.taskOut.from_orm(task) for task in tasks],
        status=status.HTTP_200_OK,
        message="Tasks retrieved successfully"
    )

@router.get("/{id}", response_model=schemas.taskOut)
def get_task(id: int, db: Session = Depends(get_db), current_user=Depends(oauth2.get_current_user)):
    """Get a single task by ID"""
    task = (
        db.query(models.Task)
        .filter(models.Task.id == id, models.Task.user_id == current_user.id)
        .first()
    )

    if not task:
        return schemas.taskOut(
            status=status.HTTP_404_NOT_FOUND,
            message=f"Task with id: {id} does not exist"
        )

    return schemas.taskOut(
        **task.__dict__,
        status=status.HTTP_200_OK,
        message="Task retrieved successfully"
    )

@router.delete("/{id}", response_model=schemas.taskOut)
def delete_task(id: int, db: Session = Depends(get_db), current_user=Depends(oauth2.get_current_user)):
    """Delete a task"""
    task = (
        db.query(models.Task)
        .filter(models.Task.id == id, models.Task.user_id == current_user.id)
        .first()
    )

    if not task:
        return schemas.taskOut(
            status=status.HTTP_404_NOT_FOUND,
            message=f"Task with id: {id} does not exist"
        )

    try:
        db.delete(task)
        db.commit()

    except Exception as e:
        db.rollback()
        add_error(e, db)
        return schemas.taskOut(
            status=status.HTTP_400_BAD_REQUEST,
            message="Failed to delete task"
        )

    return schemas.taskOut(
        status=status.HTTP_200_OK,
        message="Task deleted successfully"
    )

@router.put('/mark_as_done/{id}', response_model=schemas.taskOut)
def mark_task_as_done(id: int, db: Session = Depends(get_db), current_user=Depends(oauth2.get_current_user)):
    """Mark a task as done"""
    task_query = db.query(models.Task).filter(models.Task.id == id, models.Task.user_id == current_user.id)
    db_task = task_query.first()

    if not db_task:
        return schemas.taskOut(
            status=status.HTTP_404_NOT_FOUND,
            message=f"Task with id: {id} does not exist"
        )

    try:
        task_query.update({"state": enums.State.done})
        db.commit()
        db.refresh(db_task)

    except Exception as e:
        db.rollback()
        add_error(e, db)
        return schemas.taskOut(
            status=status.HTTP_400_BAD_REQUEST,
            message="Failed to mark task as done"
        )

    return schemas.taskOut(
        **db_task.__dict__,
        status=status.HTTP_200_OK,
        message="Task marked as done successfully"
    )

@router.put('/toggle_state/{id}', response_model=schemas.taskOut)
def toggle_task_state(id: int, db: Session = Depends(get_db), current_user=Depends(oauth2.get_current_user)):
    """Toggle task state: todo -> doing -> done -> todo"""
    task_query = db.query(models.Task).filter(models.Task.id == id, models.Task.user_id == current_user.id)
    db_task = task_query.first()

    if not db_task:
        return schemas.taskOut(
            status=status.HTTP_404_NOT_FOUND,
            message=f"Task with id: {id} does not exist"
        )

    try:
        if db_task.state == enums.State.todo:
            new_state = enums.State.doing
        elif db_task.state == enums.State.doing:
            new_state = enums.State.done
        else:
            new_state = enums.State.todo

        task_query.update({"state": new_state})
        db.commit()
        db.refresh(db_task)

    except Exception as e:
        db.rollback()
        add_error(e, db)
        return schemas.taskOut(
            status=status.HTTP_400_BAD_REQUEST,
            message="Failed to toggle task state"
        )

    return schemas.taskOut(
        **db_task.__dict__,
        status=status.HTTP_200_OK,
        message=f"Task state changed to {new_state.value}"
    )
                   
@router.put("/{id}", response_model=schemas.taskOut)
def update_task(id: int, task: schemas.taskIn, db: Session = Depends(get_db), current_user=Depends(oauth2.get_current_user)):
    """Update a task"""
    query = db.query(models.Task).filter(models.Task.id == id, models.Task.user_id == current_user.id)
    db_task = query.first()

    if not db_task:
        return schemas.taskOut(
            status=status.HTTP_404_NOT_FOUND,
            message=f"Task with id: {id} does not exist"
        )

    try:
        query.update(task.model_dump(exclude_unset=True))
        db.commit()
        db.refresh(db_task)

    except Exception as e:
        db.rollback()
        add_error(e, db)
        return schemas.taskOut(
            status=status.HTTP_400_BAD_REQUEST,
            message="Failed to update task"
        )

    return schemas.taskOut(
        **db_task.__dict__,
        status=status.HTTP_200_OK,
        message="Task updated successfully"
    )

@router.get("/stats/summary", response_model=dict)
def get_task_stats(db: Session = Depends(get_db), current_user=Depends(oauth2.get_current_user)):
    """Get task statistics for the current user"""
    try:
        total_tasks = db.query(models.Task).filter(models.Task.user_id == current_user.id).count()
        
        todo_count = db.query(models.Task).filter(
            models.Task.user_id == current_user.id,
            models.Task.state == enums.State.todo
        ).count()
        
        doing_count = db.query(models.Task).filter(
            models.Task.user_id == current_user.id,
            models.Task.state == enums.State.doing
        ).count()
        
        done_count = db.query(models.Task).filter(
            models.Task.user_id == current_user.id,
            models.Task.state == enums.State.done
        ).count()
        
        overdue_count = db.query(models.Task).filter(
            models.Task.user_id == current_user.id,
            models.Task.due_date < datetime.now(),
            models.Task.state != enums.State.done
        ).count()

        return {
            "status": status.HTTP_200_OK,
            "message": "Statistics retrieved successfully",
            "data": {
                "total": total_tasks,
                "todo": todo_count,
                "doing": doing_count,
                "done": done_count,
                "overdue": overdue_count,
                "completion_rate": round((done_count / total_tasks * 100) if total_tasks > 0 else 0, 2)
            }
        }

    except Exception as e:
        add_error(e, db)
        return {
            "status": status.HTTP_400_BAD_REQUEST,
            "message": "Failed to retrieve statistics"
        }