# One-Step Server Deployment

这个版本就是给“阿里云基础镜像、只有 `yum/dnf`、没有 `apt`、没有 Go、没有 MySQL、没有 MinIO”的情况准备的。

它会做两类事情：

1. 安装宿主机依赖
- Go
- Docker
- 防火墙工具

2. 拉起业务依赖和后端
- 用 Docker 启动 MySQL
- 用 Docker 启动 MinIO
- 创建数据库、用户和 3 张表
- 编译 Go 后端可执行文件
- 生成 systemd 服务并启动

## 使用前提

- 阿里云 Linux / CentOS / Rocky / AlmaLinux 这类带 `yum` 或 `dnf` 的系统优先
- 也兼容 `apt-get`
- 代码仓库已经 clone 到服务器
- 使用 `root` 或 `sudo` 执行

## 保留文件

- `one_step.env.example`
- `one_step.sh`
- `clean.sh`
- `ONE_STEP.md`

## 使用方式

1. 进入目录

```bash
cd Backend/deploy
```

2. 复制环境文件

```bash
cp one_step.env.example one_step.env
```

3. 至少修改这些值

- `MYSQL_ROOT_PASSWORD`
- `MYSQL_APP_PASSWORD`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `PUBLIC_IP`

如果服务器访问海外网络不稳定，建议保留默认：

- `GO_PROXY=http://mirrors.cloud.aliyuncs.com/goproxy/,https://goproxy.cn,direct`
- `GO_SUMDB=off`

4. 执行脚本

```bash
sudo bash ./one_step.sh
```

## 执行完成后的默认访问地址

- 后端：`http://你的公网IP:8080`
- 健康检查：`http://你的公网IP:8080/health`
- MinIO API：`http://你的公网IP:9000`
- MinIO Console：`http://你的公网IP:9001`

## 生成位置

- 后端二进制：`/opt/short-drama/bin/short-drama-backend`
- 后端环境变量：`/etc/short-drama/backend.env`
- MySQL 数据目录：`/opt/short-drama/mysql/data`
- MinIO 数据目录：`/opt/short-drama/minio/data`

## 清理

停止并清理部署出来的服务：

```bash
cd Backend/deploy
sudo bash ./clean.sh
```

如果还要删数据库和对象存储数据：

```bash
sudo bash ./clean.sh --purge-data
```

## 说明

- 这个版本里 MySQL 不再依赖系统包安装，而是直接使用官方 MySQL 容器，更适合 `yum` 环境。
- 针对阿里云 Linux 常见的 `podman-docker` 冲突，脚本会先清理冲突包，再安装 Docker CE。
- MinIO 必须使用社区镜像，例如 `quay.io/minio/minio`。不要把 `aistor/minio` 用在这个脚本里，否则会遇到许可证过期导致 bucket 无法创建。
- Go 依赖下载默认优先使用阿里云 Go Module 代理。阿里云镜像站说明其 Go 代理可用于避免 DNS 污染和拉取失败；其 VPC 网络地址为 `http://mirrors.cloud.aliyuncs.com/`。为提高单机部署成功率，脚本默认将 `GO_SUMDB` 设为 `off`。
- 如果脚本跑完后本机访问正常，但公网访问不到，通常是云厂商安全组没有放行 `8080`、`9000`、`9001`。
- 当前是单机部署，适合开发、测试和早期上线。
