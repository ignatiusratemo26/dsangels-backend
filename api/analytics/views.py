from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg, F, Q, Window
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
import json

from core.models import UserActivity, User, Content, Challenge, UserProgress
from core.serializers import UserActivitySerializer

class UserActivityListView(generics.ListAPIView):
    """
    List user activities (staff only or user's own activities)
    """
    serializer_class = UserActivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Staff can see all activities, regular users only see their own
        if user.is_staff:
            queryset = UserActivity.objects.all()
            
            # Filter by user_id if provided
            user_id = self.request.query_params.get('user_id')
            if user_id:
                queryset = queryset.filter(user_id=user_id)
        else:
            queryset = UserActivity.objects.filter(user=user)
        
        # Filter by activity type if provided
        activity_type = self.request.query_params.get('activity_type')
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
            
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
            
        # Filter by content type
        content_type = self.request.query_params.get('content_type')
        if content_type:
            try:
                ct = ContentType.objects.get(model=content_type)
                queryset = queryset.filter(content_type=ct)
            except ContentType.DoesNotExist:
                pass
                
        return queryset.order_by('-timestamp')

class UserActivityCreateView(APIView):
    """
    Log user activity
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        activity_type = request.data.get('activity_type')
        
        if not activity_type:
            return Response(
                {'error': 'activity_type is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Get content object if provided
        content_type_str = request.data.get('content_type')
        object_id = request.data.get('object_id')
        
        content_object = None
        if content_type_str and object_id:
            try:
                app_label, model = content_type_str.split('.')
                ct = ContentType.objects.get(app_label=app_label, model=model)
                content_object = ct.get_object_for_this_type(id=object_id)
            except (ValueError, ContentType.DoesNotExist):
                pass
            
        # Extract additional data
        data = {}
        for key, value in request.data.items():
            if key not in ['activity_type', 'content_type', 'object_id']:
                data[key] = value
                
        # Get device information
        device_type = request.META.get('HTTP_USER_AGENT', '')[:50]
        ip_address = request.META.get('REMOTE_ADDR')
        session_id = request.session.session_key
        
        # Create activity
        activity = UserActivity.log(
            user=user,
            activity_type=activity_type,
            content_object=content_object,
            device_type=device_type,
            ip_address=ip_address,
            session_id=session_id,
            **data
        )
        
        return Response(UserActivitySerializer(activity).data, status=status.HTTP_201_CREATED)

class UserAnalyticsView(APIView):
    """
    Get analytics for a specific user or the authenticated user
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Staff can request data for any user
        user_id = request.query_params.get('user_id')
        if user_id and request.user.is_staff:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            user = request.user
            
        # Date range filters
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)  # Default to last 30 days
        
        date_param = request.query_params.get('days')
        if date_param:
            try:
                start_date = end_date - timedelta(days=int(date_param))
            except ValueError:
                pass
                
        # Get activity counts by type
        activities = UserActivity.objects.filter(
            user=user,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        )
        
        activity_counts = activities.values('activity_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Get completed content
        completed_content = UserProgress.objects.filter(
            user=user,
            completion_percentage=100,
            completed_at__gte=start_date
        ).count()
        
        # Calculate active days
        active_days = activities.annotate(
            day=TruncDay('timestamp')
        ).values('day').distinct().count()
        
        # Calculate streak (consecutive days with activity)
        streak = self._calculate_streak(user)
        
        # Get most active content types
        content_type_activity = activities.values(
            'content_type__model'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Get activity timeline
        timeline = activities.annotate(
            day=TruncDay('timestamp')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
        # Format the timeline data
        timeline_data = [
            {
                'date': entry['day'].strftime('%Y-%m-%d'),
                'count': entry['count']
            }
            for entry in timeline
        ]
        
        return Response({
            'user_id': user.id,
            'username': user.username,
            'activity_summary': activity_counts,
            'total_activities': activities.count(),
            'completed_content': completed_content,
            'active_days': active_days,
            'current_streak': streak,
            'content_type_activity': content_type_activity,
            'timeline': timeline_data,
            'date_range': {
                'start': start_date.date().isoformat(),
                'end': end_date.date().isoformat(),
            }
        })
    
    def _calculate_streak(self, user):
        """Calculate the user's current streak of consecutive days with activity"""
        today = timezone.now().date()
        
        # Get dates with activity, ordered from newest to oldest
        activity_dates = UserActivity.objects.filter(
            user=user
        ).annotate(
            date=TruncDay('timestamp')
        ).values('date').distinct().order_by('-date')
        
        if not activity_dates:
            return 0
            
        # Check if there's activity today
        latest_activity = activity_dates[0]['date'].date()
        if (today - latest_activity).days > 1:  # No activity today or yesterday
            return 0
            
        # Count consecutive days
        streak = 1
        for i in range(len(activity_dates) - 1):
            current_date = activity_dates[i]['date'].date()
            next_date = activity_dates[i + 1]['date'].date()
            
            if (current_date - next_date).days == 1:
                streak += 1
            else:
                break
                
        return streak

class ContentAnalyticsView(APIView):
    """
    Get analytics for content engagement (staff only)
    """
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        content_id = request.query_params.get('content_id')
        challenge_id = request.query_params.get('challenge_id')
        
        # Date range filters
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)  # Default to last 30 days
        
        date_param = request.query_params.get('days')
        if date_param:
            try:
                start_date = end_date - timedelta(days=int(date_param))
            except ValueError:
                pass
        
        if content_id:
            try:
                content_type = ContentType.objects.get(model='content')
                activities = UserActivity.objects.filter(
                    content_type=content_type,
                    object_id=content_id,
                    timestamp__gte=start_date
                )
                
                content = Content.objects.get(id=content_id)
                content_title = content.title
                
            except (ContentType.DoesNotExist, Content.DoesNotExist):
                return Response(
                    {'error': 'Content not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
        elif challenge_id:
            try:
                content_type = ContentType.objects.get(model='challenge')
                activities = UserActivity.objects.filter(
                    content_type=content_type,
                    object_id=challenge_id,
                    timestamp__gte=start_date
                )
                
                challenge = Challenge.objects.get(id=challenge_id)
                content_title = challenge.title
                
            except (ContentType.DoesNotExist, Challenge.DoesNotExist):
                return Response(
                    {'error': 'Challenge not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            return Response(
                {'error': 'Either content_id or challenge_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Get engagement metrics
        views = activities.filter(activity_type='view').count()
        completions = activities.filter(activity_type='complete').count()
        starts = activities.filter(activity_type='start').count()
        likes = activities.filter(activity_type='like').count()
        shares = activities.filter(activity_type='share').count()
        
        # Get progress for this content/challenge
        completion_rate = 0
        avg_time_spent = 0
        
        if content_id:
            progress_entries = UserProgress.objects.filter(content_id=content_id)
        else:
            progress_entries = UserProgress.objects.filter(challenge_id=challenge_id)
            
        if progress_entries.exists():
            avg_completion = progress_entries.aggregate(
                avg=Avg('completion_percentage')
            )['avg'] or 0
            completion_rate = avg_completion
            
            # Calculate average time spent if available in activity data
            time_entries = activities.filter(
                activity_type__in=['complete', 'view'],
                data__has_key='time_spent'
            )
            
            if time_entries.exists():
                time_values = []
                for entry in time_entries:
                    try:
                        time_spent = float(entry.data.get('time_spent', 0))
                        if time_spent > 0:
                            time_values.append(time_spent)
                    except (ValueError, TypeError):
                        pass
                
                if time_values:
                    avg_time_spent = sum(time_values) / len(time_values)
        
        # Get activity timeline
        timeline = activities.annotate(
            day=TruncDay('timestamp')
        ).values('day', 'activity_type').annotate(
            count=Count('id')
        ).order_by('day', 'activity_type')
        
        # Format the timeline data
        timeline_data = {}
        for entry in timeline:
            date_str = entry['day'].strftime('%Y-%m-%d')
            if date_str not in timeline_data:
                timeline_data[date_str] = {
                    'view': 0, 'complete': 0, 'start': 0, 'like': 0, 'share': 0
                }
            timeline_data[date_str][entry['activity_type']] = entry['count']
        
        return Response({
            'title': content_title,
            'id': content_id or challenge_id,
            'type': 'content' if content_id else 'challenge',
            'engagement': {
                'views': views,
                'completions': completions,
                'starts': starts,
                'completion_rate': round(completion_rate, 2),
                'likes': likes,
                'shares': shares,
                'avg_time_spent_seconds': round(avg_time_spent, 2)
            },
            'unique_users': activities.values('user').distinct().count(),
            'timeline': [
                {'date': date, **counts} for date, counts in timeline_data.items()
            ],
            'date_range': {
                'start': start_date.date().isoformat(),
                'end': end_date.date().isoformat(),
            }
        })

class EngagementStatsView(APIView):
    """
    Get platform-wide engagement statistics (staff only)
    """
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        # Date range filters
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)  # Default to last 30 days
        
        date_param = request.query_params.get('days')
        if date_param:
            try:
                start_date = end_date - timedelta(days=int(date_param))
            except ValueError:
                pass
                
        # Get overall user metrics
        total_users = User.objects.count()
        new_users = User.objects.filter(
            date_joined__gte=start_date
        ).count()
        
        active_users = UserActivity.objects.filter(
            timestamp__gte=start_date
        ).values('user').distinct().count()
        
        # Get content metrics
        content_views = UserActivity.objects.filter(
            activity_type='view',
            timestamp__gte=start_date
        ).count()
        
        content_completions = UserActivity.objects.filter(
            activity_type='complete',
            timestamp__gte=start_date
        ).count()
        
        # Get engagement metrics by day
        daily_engagement = UserActivity.objects.filter(
            timestamp__gte=start_date
        ).annotate(
            day=TruncDay('timestamp')
        ).values('day').annotate(
            users=Count('user', distinct=True),
            activities=Count('id')
        ).order_by('day')
        
        # Format the daily engagement data
        daily_data = [
            {
                'date': entry['day'].strftime('%Y-%m-%d'),
                'active_users': entry['users'],
                'activities': entry['activities']
            }
            for entry in daily_engagement
        ]
        
        # Get most popular content
        content_type_content = ContentType.objects.get(model='content')
        popular_content = UserActivity.objects.filter(
            content_type=content_type_content,
            timestamp__gte=start_date
        ).values(
            'object_id'
        ).annotate(
            views=Count('id', filter=Q(activity_type='view')),
            completions=Count('id', filter=Q(activity_type='complete')),
            total=Count('id')
        ).order_by('-total')[:10]
        
        # Add content titles
        for item in popular_content:
            try:
                content = Content.objects.get(id=item['object_id'])
                item['title'] = content.title
            except Content.DoesNotExist:
                item['title'] = f"Content {item['object_id']}"
        
        return Response({
            'users': {
                'total': total_users,
                'new': new_users,
                'active': active_users,
                'retention_rate': round((active_users / total_users) * 100, 2) if total_users else 0
            },
            'content': {
                'views': content_views,
                'completions': content_completions,
                'completion_rate': round((content_completions / content_views) * 100, 2) if content_views else 0
            },
            'daily_engagement': daily_data,
            'popular_content': popular_content,
            'date_range': {
                'start': start_date.date().isoformat(),
                'end': end_date.date().isoformat(),
            }
        })

class ActivityTimelineView(APIView):
    """
    Get activity timeline for a user or the platform
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user_id = request.query_params.get('user_id')
        
        # Staff can request data for any user or all users
        if user_id and request.user.is_staff:
            try:
                user = User.objects.get(id=user_id)
                activities = UserActivity.objects.filter(user=user)
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        elif request.user.is_staff and not user_id:
            # Staff requesting platform-wide data
            activities = UserActivity.objects.all()
        else:
            # Regular user can only see their own data
            activities = UserActivity.objects.filter(user=request.user)
        
        # Date range filters
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)  # Default to last 30 days
        
        date_param = request.query_params.get('days')
        if date_param:
            try:
                start_date = end_date - timedelta(days=int(date_param))
            except ValueError:
                pass
                
        activities = activities.filter(timestamp__gte=start_date)
        
        # Get timeline grouping
        grouping = request.query_params.get('grouping', 'day')
        valid_groupings = ['day', 'week', 'month']
        
        if grouping not in valid_groupings:
            grouping = 'day'
            
        # Select the appropriate truncation function
        trunc_func = TruncDay
        if grouping == 'week':
            trunc_func = TruncWeek
        elif grouping == 'month':
            trunc_func = TruncMonth
            
        # Group activities by time period and activity type
        timeline = activities.annotate(
            period=trunc_func('timestamp')
        ).values('period', 'activity_type').annotate(
            count=Count('id')
        ).order_by('period', 'activity_type')
        
        # Format the timeline data
        formatted_timeline = []
        current_period = None
        period_data = {}
        
        for entry in timeline:
            period_str = entry['period'].strftime('%Y-%m-%d')
            
            if current_period != period_str:
                if current_period:
                    formatted_timeline.append({'date': current_period, **period_data})
                
                current_period = period_str
                period_data = {
                    'view': 0, 'complete': 0, 'start': 0, 'like': 0, 
                    'share': 0, 'comment': 0, 'login': 0, 'other': 0
                }
                
            activity_type = entry['activity_type']
            if activity_type in period_data:
                period_data[activity_type] = entry['count']
            else:
                period_data['other'] = period_data.get('other', 0) + entry['count']
        
        # Add the last period
        if current_period:
            formatted_timeline.append({'date': current_period, **period_data})
            
        return Response({
            'timeline': formatted_timeline,
            'grouping': grouping,
            'date_range': {
                'start': start_date.date().isoformat(),
                'end': end_date.date().isoformat(),
            }
        })