from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional
from datetime import date, datetime
from enum import Enum
import sqlite3
import os
from contextlib import contextmanager

app = FastAPI(title="HRMS Lite API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DATABASE_PATH = os.getenv("DATABASE_PATH", "hrms.db")

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create employees table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                employee_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                department TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Create attendance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees (employee_id) ON DELETE CASCADE,
                UNIQUE(employee_id, date)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_attendance_employee 
            ON attendance(employee_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_attendance_date 
            ON attendance(date)
        """)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

# Pydantic models
class AttendanceStatus(str, Enum):
    PRESENT = "Present"
    ABSENT = "Absent"

class EmployeeCreate(BaseModel):
    employee_id: str = Field(..., min_length=1, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    department: str = Field(..., min_length=1, max_length=100)
    
    @validator('employee_id')
    def validate_employee_id(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError('Employee ID cannot be empty')
        return v.strip()

    @validator('full_name')
    def validate_full_name(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError('Full name cannot be empty')
        return v.strip()

    @validator('department')
    def validate_department(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError('Department cannot be empty')
        return v.strip()

class EmployeeResponse(BaseModel):
    employee_id: str
    full_name: str
    email: str
    department: str
    created_at: str

class AttendanceCreate(BaseModel):
    employee_id: str
    date: date
    status: AttendanceStatus
    
    @validator('date')
    def validate_date(cls, v):
        if v > date.today():
            raise ValueError('Cannot mark attendance for future dates')
        return v

class AttendanceResponse(BaseModel):
    id: int
    employee_id: str
    date: str
    status: str
    created_at: str
    employee_name: Optional[str] = None
    employee_department: Optional[str] = None

class DashboardStats(BaseModel):
    total_employees: int
    total_attendance_records: int
    present_today: int
    absent_today: int

# API Endpoints
@app.get("/")
async def root():
    return {"message": "HRMS Lite API", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Employee Management Endpoints
@app.post("/api/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(employee: EmployeeCreate):
    """Create a new employee"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if employee_id already exists
        cursor.execute("SELECT employee_id FROM employees WHERE employee_id = ?", (employee.employee_id,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee with ID '{employee.employee_id}' already exists"
            )
        
        # Check if email already exists
        cursor.execute("SELECT email FROM employees WHERE email = ?", (employee.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee with email '{employee.email}' already exists"
            )
        
        created_at = datetime.now().isoformat()
        
        try:
            cursor.execute(
                """
                INSERT INTO employees (employee_id, full_name, email, department, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (employee.employee_id, employee.full_name, employee.email, employee.department, created_at)
            )
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create employee. Please check the data and try again."
            )
        
        return EmployeeResponse(
            employee_id=employee.employee_id,
            full_name=employee.full_name,
            email=employee.email,
            department=employee.department,
            created_at=created_at
        )

@app.get("/api/employees", response_model=List[EmployeeResponse])
async def get_employees():
    """Get all employees"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT employee_id, full_name, email, department, created_at FROM employees ORDER BY created_at DESC"
        )
        employees = cursor.fetchall()
        
        return [
            EmployeeResponse(
                employee_id=emp["employee_id"],
                full_name=emp["full_name"],
                email=emp["email"],
                department=emp["department"],
                created_at=emp["created_at"]
            )
            for emp in employees
        ]

@app.get("/api/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(employee_id: str):
    """Get a specific employee by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT employee_id, full_name, email, department, created_at FROM employees WHERE employee_id = ?",
            (employee_id,)
        )
        employee = cursor.fetchone()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID '{employee_id}' not found"
            )
        
        return EmployeeResponse(
            employee_id=employee["employee_id"],
            full_name=employee["full_name"],
            email=employee["email"],
            department=employee["department"],
            created_at=employee["created_at"]
        )

@app.delete("/api/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(employee_id: str):
    """Delete an employee"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if employee exists
        cursor.execute("SELECT employee_id FROM employees WHERE employee_id = ?", (employee_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID '{employee_id}' not found"
            )
        
        # Delete attendance records first
        cursor.execute("DELETE FROM attendance WHERE employee_id = ?", (employee_id,))
        
        # Delete employee
        cursor.execute("DELETE FROM employees WHERE employee_id = ?", (employee_id,))
        
        return None

# Attendance Management Endpoints
@app.post("/api/attendance", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
async def mark_attendance(attendance: AttendanceCreate):
    """Mark attendance for an employee"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if employee exists
        cursor.execute("SELECT employee_id FROM employees WHERE employee_id = ?", (attendance.employee_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID '{attendance.employee_id}' not found"
            )
        
        created_at = datetime.now().isoformat()
        date_str = attendance.date.isoformat()
        
        try:
            # Try to insert new attendance record
            cursor.execute(
                """
                INSERT INTO attendance (employee_id, date, status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (attendance.employee_id, date_str, attendance.status.value, created_at)
            )
            attendance_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            # If record exists, update it
            cursor.execute(
                """
                UPDATE attendance 
                SET status = ?, created_at = ?
                WHERE employee_id = ? AND date = ?
                """,
                (attendance.status.value, created_at, attendance.employee_id, date_str)
            )
            
            cursor.execute(
                "SELECT id FROM attendance WHERE employee_id = ? AND date = ?",
                (attendance.employee_id, date_str)
            )
            result = cursor.fetchone()
            attendance_id = result["id"]
        
        return AttendanceResponse(
            id=attendance_id,
            employee_id=attendance.employee_id,
            date=date_str,
            status=attendance.status.value,
            created_at=created_at
        )

@app.get("/api/attendance", response_model=List[AttendanceResponse])
async def get_attendance(
    employee_id: Optional[str] = None,
    date: Optional[date] = None,
    on_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """Get attendance records with optional filters"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT a.id, a.employee_id, a.date, a.status, a.created_at,
                   e.full_name as employee_name, e.department as employee_department
            FROM attendance a
            LEFT JOIN employees e ON a.employee_id = e.employee_id
            WHERE 1=1
        """
        params = []
        
        if employee_id:
            query += " AND a.employee_id = ?"
            params.append(employee_id)
        
        # Accept either `date` or `on_date` as the specific-date filter (frontend may send either)
        specific_date = on_date or date
        if specific_date:
            query += " AND a.date = ?"
            params.append(specific_date.isoformat())
        
        if start_date:
            query += " AND a.date >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND a.date <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY a.date DESC, a.employee_id"
        
        cursor.execute(query, params)
        records = cursor.fetchall()
        
        return [
            AttendanceResponse(
                id=record["id"],
                employee_id=record["employee_id"],
                date=record["date"],
                status=record["status"],
                created_at=record["created_at"],
                employee_name=record["employee_name"],
                employee_department=record["employee_department"]
            )
            for record in records
        ]

@app.get("/api/attendance/employee/{employee_id}/summary")
async def get_employee_attendance_summary(employee_id: str):
    """Get attendance summary for a specific employee"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if employee exists
        cursor.execute("SELECT full_name FROM employees WHERE employee_id = ?", (employee_id,))
        employee = cursor.fetchone()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID '{employee_id}' not found"
            )
        
        # Get attendance summary
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total_days,
                SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present_days,
                SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent_days
            FROM attendance
            WHERE employee_id = ?
            """,
            (employee_id,)
        )
        summary = cursor.fetchone()
        
        return {
            "employee_id": employee_id,
            "employee_name": employee["full_name"],
            "total_days": summary["total_days"] or 0,
            "present_days": summary["present_days"] or 0,
            "absent_days": summary["absent_days"] or 0
        }

@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get dashboard statistics"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Total employees
        cursor.execute("SELECT COUNT(*) as count FROM employees")
        total_employees = cursor.fetchone()["count"]
        
        # Total attendance records
        cursor.execute("SELECT COUNT(*) as count FROM attendance")
        total_attendance_records = cursor.fetchone()["count"]
        
        # Today's attendance
        today = date.today().isoformat()
        cursor.execute(
            "SELECT COUNT(*) as count FROM attendance WHERE date = ? AND status = 'Present'",
            (today,)
        )
        present_today = cursor.fetchone()["count"]
        
        cursor.execute(
            "SELECT COUNT(*) as count FROM attendance WHERE date = ? AND status = 'Absent'",
            (today,)
        )
        absent_today = cursor.fetchone()["count"]
        
        return DashboardStats(
            total_employees=total_employees,
            total_attendance_records=total_attendance_records,
            present_today=present_today,
            absent_today=absent_today
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
