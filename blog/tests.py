from django.test import TestCase
from django.utils import timezone

from .models import Post
from .wordpress import clean_html, first_paragraph


class CleanHtmlTests(TestCase):
    def test_strips_block_comments_classes_and_wrappers(self):
        raw = (
            '<!-- wp:paragraph -->\n<p class="x" style="color:red">Hi <strong>there</strong></p>\n<!-- /wp:paragraph -->'
            '<div class="wp-block-group"><h2 class="wp-block-heading">Title</h2></div>'
        )
        self.assertEqual(clean_html(raw), '<p>Hi <strong>there</strong></p>\n<h2>Title</h2>')

    def test_drops_scripts_and_unknown_attributes(self):
        cleaned = clean_html('<p onclick="x()">a</p><script>alert(1)</script><a href="/b" target="_blank">b</a>')
        self.assertEqual(cleaned, '<p>a</p><a href="/b">b</a>')

    def test_code_block_pro_becomes_plain_pre(self):
        raw = (
            '<!-- wp:kevinbatdorf/code-block-pro {"code":"if a \\u0026amp; b:\\n    pass","codeHTML":"..."} -->'
            '<div class="wp-block-kevinbatdorf-code-block-pro"><pre class="shiki">ignored</pre></div>'
            '<!-- /wp:kevinbatdorf/code-block-pro -->'
        )
        self.assertEqual(clean_html(raw), '<pre><code>if a &amp; b:\n    pass</code></pre>')

    def test_first_paragraph_is_trimmed_on_a_word(self):
        excerpt = first_paragraph('<p>' + 'word ' * 100 + '</p>', limit=20)
        self.assertEqual(excerpt, 'word word word word…')


class PostPagesTests(TestCase):
    def setUp(self):
        self.post = Post.objects.create(
            title='Hello', slug='hello', body='<p>' + 'word ' * 450 + '</p>', published_at=timezone.now(),
        )
        Post.objects.create(title='Draft', slug='draft', body='<p>x</p>', published_at=timezone.now(), is_published=False)

    def test_reading_time(self):
        self.assertEqual(self.post.reading_minutes, 3)

    def test_list_hides_drafts(self):
        response = self.client.get('/posts/')
        self.assertContains(response, 'Hello')
        self.assertNotContains(response, 'Draft')

    def test_detail_and_draft_404(self):
        self.assertContains(self.client.get('/posts/hello/'), '3 min read')
        self.assertEqual(self.client.get('/posts/draft/').status_code, 404)


class LaunchTests(TestCase):
    def setUp(self):
        Post.objects.create(title='Hello', slug='hello', body='<p>x</p>', published_at=timezone.now())

    def test_old_wordpress_links_redirect_for_good(self):
        response = self.client.get('/hello/')
        self.assertEqual((response.status_code, response['Location']), (301, '/posts/hello/'))
        self.assertEqual(self.client.get('/home/')['Location'], '/')

    def test_unknown_old_link_is_404(self):
        response = self.client.get('/no-such-post/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "This page doesn't exist.", status_code=404)

    def test_sitemap_and_robots(self):
        sitemap = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('/posts/hello/', sitemap)
        self.assertIn('/metrics/gdp-per-capita/', sitemap)
        self.assertIn('Sitemap: http://testserver/sitemap.xml', self.client.get('/robots.txt').content.decode())
