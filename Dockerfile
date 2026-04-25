FROM python:3.11-slim

LABEL maintainer="Kubenew"
LABEL description="PrivateCloud: Kubernetes private cloud installer"

ARG VERSION=0.7.0

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    openssh-client \
    git \
    gnupg \
    lsb-release \
    apt-transport-https \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl
RUN curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.29/deb/Release.key | gpg --dearmor -o /usr/share/keyrings/kubernetes-apt-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.29/deb/ /" > /etc/apt/sources.list.d/kubernetes.list \
    && apt-get update && apt-get install -y kubectl \
    && rm -rf /var/lib/apt/lists/*

# Install Helm
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install Terraform
RUN curl -fsSL https://releases.hashicorp.com/terraform/1.7.0/terraform_1.7.0_linux_amd64.zip -o /tmp/terraform.zip \
    && apt-get update && apt-get install -y --no-install-recommends unzip \
    && unzip /tmp/terraform.zip -d /usr/local/bin/ \
    && rm /tmp/terraform.zip \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir privatecloud==${VERSION}

RUN mkdir -p /root/.kube /root/.ssh

ENV KUBECONFIG=/root/.kube/config
ENV TERM=xterm
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

COPY examples /app/examples

RUN privatecloud init --help > /dev/null 2>&1 || true

ENTRYPOINT ["privatecloud"]
CMD ["--help"]

EXPOSE 5000 8080

# Example usage:
# docker build -t privatecloud .
# docker run -it --rm privatecloud init
# docker run -it --rm privatecloud doctor
# docker run -d -p 8080:5000 --name privatecloud-gui privatecloud gui --port 5000 --host 0.0.0.0