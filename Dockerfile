FROM odoo:19

USER root

# Install system dependencies for WeasyPrint (Pango, Cairo, etc.)
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install WeasyPrint python package
RUN pip3 install --no-cache-dir weasyprint --break-system-packages

USER odoo
