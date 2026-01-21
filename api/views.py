from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from datetime import date
from .models import Employee, Attendance
from .serializers import (
    EmployeeSerializer,
    AttendanceSerializer,
    DashboardStatsSerializer
)


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    lookup_field = 'employee_id'


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.select_related('employee').all()
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by employee_id
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            queryset = queryset.filter(employee__employee_id=employee_id)
        
        # Filter by specific date (accept both 'date' and 'on_date' params)
        specific_date = self.request.query_params.get('on_date') or self.request.query_params.get('date')
        if specific_date:
            queryset = queryset.filter(date=specific_date)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset

    @action(detail=False, methods=['get'], url_path='employee/(?P<employee_id>[^/.]+)/summary')
    def employee_summary(self, request, employee_id=None):
        try:
            employee = Employee.objects.get(employee_id=employee_id)
        except Employee.DoesNotExist:
            return Response(
                {"detail": f"Employee with ID '{employee_id}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        attendance_summary = Attendance.objects.filter(employee=employee).aggregate(
            total_days=Count('id'),
            present_days=Count('id', filter=Q(status='Present')),
            absent_days=Count('id', filter=Q(status='Absent'))
        )
        
        return Response({
            'employee_id': employee.employee_id,
            'employee_name': employee.full_name,
            'total_days': attendance_summary['total_days'] or 0,
            'present_days': attendance_summary['present_days'] or 0,
            'absent_days': attendance_summary['absent_days'] or 0,
        })


class DashboardViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        total_employees = Employee.objects.count()
        total_attendance_records = Attendance.objects.count()
        
        today = date.today()
        present_today = Attendance.objects.filter(date=today, status='Present').count()
        absent_today = Attendance.objects.filter(date=today, status='Absent').count()
        
        data = {
            'total_employees': total_employees,
            'total_attendance_records': total_attendance_records,
            'present_today': present_today,
            'absent_today': absent_today,
        }
        
        serializer = DashboardStatsSerializer(data)
        return Response(serializer.data)
