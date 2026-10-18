from django.shortcuts import get_object_or_404, render

from .models import Post


def post_list(request):
    posts = Post.published.prefetch_related('categories')
    return render(request, 'blog/post_list.html', {'posts': posts})


def post_detail(request, slug):
    post = get_object_or_404(Post.published.prefetch_related('categories'), slug=slug)
    newer = Post.published.filter(published_at__gt=post.published_at).order_by('published_at').first()
    older = Post.published.filter(published_at__lt=post.published_at).first()
    return render(request, 'blog/post_detail.html', {'post': post, 'newer': newer, 'older': older})
