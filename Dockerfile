FROM python:3.11-slim

LABEL maintainer="Kubenew"
LABEL description="PrivateCloud: Kubernetes private cloud installer"

ARG VERSION=0.7.0

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    kubectl \
    helm \
    terraform \
    git \
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