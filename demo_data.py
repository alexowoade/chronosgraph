"""Shared offline demo web, used by both the app and the tests."""

TEMPORAL_CONFLICT_WEB = {
    "https://docs.amd-cloud.example/index.html": """
        <html><head><title>AMD Instinct Documentation Portal</title></head>
        <body>
            <p>Browse official hardware specifications, cloud pricing, and historical archives.</p>
            <a href="https://docs.amd-cloud.example/archive-2023-specs.html">Archived 2023 Preview Specs</a>
            <a href="https://docs.amd-cloud.example/current-2026-specs.html">Official 2026 Production Spec Sheet</a>
            <a href="https://docs.amd-cloud.example/support.html">Enterprise Support & JSON-LD</a>
        </body></html>
    """,
    "https://docs.amd-cloud.example/archive-2023-specs.html": """
        <html><head><title>2023 Early Preview</title>
        <meta property="article:modified_time" content="2023-06-15" /></head>
        <body>
            <p>In the 2023 v1.0 early preview, the accelerator memory capacity was 128 GB HBM3 with 4.0 TB/s bandwidth.</p>
        </body></html>
    """,
    "https://docs.amd-cloud.example/current-2026-specs.html": """
        <html><head><title>2026 Official Production Specs</title>
        <meta property="article:modified_time" content="2026-09-01" /></head>
        <body>
            <table>
                <tr><th>Model</th><th>Memory Capacity</th><th>Peak Bandwidth</th><th>Release</th></tr>
                <tr><td>AMD Instinct MI300X Production</td><td>192 GB HBM3</td><td>5.3 TB/s</td><td>2026 v2.4</td></tr>
            </table>
        </body></html>
    """,
    "https://docs.amd-cloud.example/support.html": """
        <html><head><title>AMD Support</title>
        <script type="application/ld+json">
        {"@type": "Organization", "name": "AMD ROCm Enterprise Support", "email": "rocm-support@amd.example.com"}
        </script></head>
        <body><p>Contact our team.</p></body></html>
    """
}
