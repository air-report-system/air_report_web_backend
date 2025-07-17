"""
用户认证视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .models import User, UserProfile
from .serializers import UserSerializer, UserProfileSerializer, LoginSerializer


class UserViewSet(viewsets.ModelViewSet):
    """用户管理视图集"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """只返回当前用户可见的用户"""
        user = self.request.user
        if user.role == 'admin':
            return User.objects.all()
        else:
            return User.objects.filter(id=user.id)


class LoginView(APIView):
    """用户登录视图"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']

            user = authenticate(username=username, password=password)
            if user:
                # 获取或创建Token
                token, created = Token.objects.get_or_create(user=user)
                return Response({
                    'message': '登录成功',
                    'user': UserSerializer(user).data,
                    'token': token.key
                })
            else:
                return Response(
                    {'error': '用户名或密码错误'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """用户登出视图"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # 删除用户的token
            token = Token.objects.get(user=request.user)
            token.delete()
            return Response({'message': '登出成功'})
        except Token.DoesNotExist:
            return Response({'message': '登出成功'})


class UserProfileView(APIView):
    """用户配置视图"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            # 如果配置不存在，创建默认配置
            profile = UserProfile.objects.create(user=request.user)
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data)

    def put(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=request.user)

        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BackgroundImageView(APIView):
    """用户背景图管理视图"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """获取用户背景图设置"""
        try:
            profile = UserProfile.objects.get(user=request.user)
            return Response({
                'background_image': profile.background_image,
                'background_opacity': profile.background_opacity
            })
        except UserProfile.DoesNotExist:
            return Response({
                'background_image': None,
                'background_opacity': 0.1
            })

    def post(self, request):
        """上传背景图"""
        try:
            profile, created = UserProfile.objects.get_or_create(user=request.user)
        except Exception:
            return Response(
                {'error': '获取用户配置失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        background_image = request.data.get('background_image')
        background_opacity = request.data.get('background_opacity', profile.background_opacity)

        # 验证数据
        serializer = UserProfileSerializer(profile, data={
            'background_image': background_image,
            'background_opacity': background_opacity
        }, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': '背景图上传成功',
                'background_image': profile.background_image,
                'background_opacity': profile.background_opacity
            })
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        """更新背景图透明度"""
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response(
                {'error': '用户配置不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        background_opacity = request.data.get('background_opacity')
        if background_opacity is None:
            return Response(
                {'error': '缺少透明度参数'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 验证透明度值
        try:
            opacity = float(background_opacity)
            if not 0 <= opacity <= 1:
                return Response(
                    {'error': '透明度必须在0-1之间'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': '透明度必须是有效的数字'},
                status=status.HTTP_400_BAD_REQUEST
            )

        profile.background_opacity = opacity
        profile.save()

        return Response({
            'message': '透明度更新成功',
            'background_opacity': profile.background_opacity
        })

    def delete(self, request):
        """删除背景图"""
        try:
            profile = UserProfile.objects.get(user=request.user)
            profile.background_image = None
            profile.background_opacity = 0.1  # 重置为默认值
            profile.save()
            
            return Response({'message': '背景图删除成功'})
        except UserProfile.DoesNotExist:
            return Response(
                {'error': '用户配置不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
