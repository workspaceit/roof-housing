from django.http import JsonResponse


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if '/health' == request.path[:7]:
            return JsonResponse({'status': 'ok'})
        else:
            response = self.get_response(request)

            return response
