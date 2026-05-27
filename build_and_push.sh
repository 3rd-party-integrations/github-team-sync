podman build --arch=arm64 . -t registry.zepto.co.in/infra-tools/github-team-sync:$1
podman push registry.zepto.co.in/infra-tools/github-team-sync:$1