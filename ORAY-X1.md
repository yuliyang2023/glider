# OrayBox X1 专用构建

适用于 MT7628 / MIPS 24KEc 的 Linux MIPS 小端软浮点设备。构建参数为
`CGO_ENABLED=0 GOOS=linux GOARCH=mipsle GOMIPS=softfloat`，不依赖设备上的 libc。
使用 Go 1.24.13，删除调试符号、源码路径和 build ID。

## GitHub Actions

打开本仓库的 Actions → **Build Oray X1** → **Run workflow**。
工作流只允许手动触发，不发布 Docker 镜像。先测试源码，再生成两个 artifact：

| 文件 | 协议 |
| --- | --- |
| `glider-oray-x1-full` | 上游默认全部协议及 Linux 功能 |
| `glider-oray-x1-lite` | HTTP、mixed、SOCKS5、SS、VMess、VLESS、Trojan、TLS、WS/WSS、reject |

精简版通过 `oray_lite` build tag 排除 KCP、SSH、SSR、smux、simple-obfs、
SOCKS4、DHCP、redir/tproxy、unix/vsock 等注册模块；默认构建行为保持一致。
DNS、规则和健康检测核心仍保留。协议支持以随包的 `HELP.txt` 和 `-scheme all` 为准。
VMess 默认 `alterID=0` 使用 AEAD；SS2022、VLESS REALITY/XTLS 等扩展不在本构建承诺范围内。

每个 artifact 含原始二进制、`.gz`、`SHA256SUMS`、`BUILD-INFO.txt`、帮助、本文档及许可证。
Actions Summary 报告真实大小。gzip 是下载压缩文件，运行前需要解压，空间应按原始文件计算。
CI 用 QEMU 的 MIPS 24KEc 执行帮助、SOCKS5 TCP 和 SS AEAD 转发测试；
真实 Oray 内核兼容性、UDP 和具体远端 VMess/SS 节点仍需设备上验证。

### 已验证的产物大小

[首次成功构建](https://github.com/yuliyang2023/glider/actions/runs/37201212234)
对应源码提交 `6c2edbb`（glider 0.17.0）：

| 版本 | 原始二进制 | gzip 下载文件 |
| --- | --- | --- |
| lite | 6,684,851 字节（6.38 MiB） | 2,253,965 字节（2.15 MiB） |
| full | 8,388,787 字节（8.00 MiB） | 2,874,911 字节（2.74 MiB） |

两版通过 QEMU MIPS 24KEc 的 SOCKS5 TCP 和 SS AEAD 转发测试。
精简版已在 Oray 的 Linux 4.4.302 上执行并通过 SOCKS5 握手；本机测试监听的空闲 RSS 为
5,016 KiB（约 4.90 MiB）。该数值不代表有流量时的内存上限，也不等于 `/tmp` 的文件占用。

## 在 Oray 上试运行

该设备可写 Flash 不足 1 MB，先放到 `/tmp`（RAM）测试，不要直接覆盖现有 HEV。
下载 artifact 并解压 ZIP 后，在 Mac 上执行：

```sh
shasum -a 256 -c SHA256SUMS
cat glider-oray-x1-lite | ssh oray 'umask 077; cat > /tmp/glider-oray-x1-lite; chmod 700 /tmp/glider-oray-x1-lite'
ssh oray '/tmp/glider-oray-x1-lite -h'
```

`/tmp` 文件重启后丢失；Go 进程还需要运行内存，二进制大小不等于运行内存占用。
先确认当前 `df -k /tmp` 和 `free`，同时使用 HEV 时应留足余量。

配置文件示例（只选一条 forward，并替换占位内容）：

```ini
listen=socks5://127.0.0.1:1080
forward=ss://chacha20-ietf-poly1305:YOUR_PASSWORD@SERVER:PORT
# 或 VMess TCP：
# forward=vmess://YOUR_UUID@SERVER:PORT?alterID=0
# 或 VMess over TLS + WS：
# forward=tls://SERVER_IP:443?serverName=SERVER_NAME,ws://@/PATH?host=SERVER_NAME,vmess://YOUR_UUID@?alterID=0
```

密码中 `@`、`:` 等 URL 特殊字符需要百分号编码。配置文件权限设置为 `600`，不要提交真实凭据。
TLS 节点需要设备时间正确、可用的 CA 证书；不要用跳过验证代替证书部署。

```sh
chmod 600 /root/glider.conf
nohup /tmp/glider-oray-x1-lite -config /root/glider.conf >/tmp/glider.log 2>&1 </dev/null &
```

在 Mac 上测试：

```sh
# Oray 的监听仅在本机，用 SSH 隧道访问：
ssh -N -L 11080:127.0.0.1:1080 oray
# 另一个终端：
curl --proxy socks5h://127.0.0.1:11080 --connect-timeout 10 https://example.com/
```

## 与现有 HEV 配合

```text
Wi-Fi / 局域网客户端 → HEV tun0 → 127.0.0.1:1080 glider → SS / VMess 等远端
```

Glider 是本机 SOCKS5 后端，HEV 和管理脚本继续负责 TUN、路由及 DNS。
现有 HEV 管理脚本会拦截路由器的 DNS 并返回映射地址，因此 Glider 的远端服务器地址
建议使用提前解析好的真实 IP；TLS 的 `serverName` 和 WS 的 `host` 则保留原域名。
这样可避免 Glider 解析上游域名后连接 HEV 映射地址、再次进入本机代理形成循环。
确认 Glider 代理可用后，再将 `/root/hev.yml` 的 SOCKS5 地址改为 `127.0.0.1`、端口 `1080`，
本地无认证时删除用户名和密码字段；然后重启 HEV 管理脚本。
Glider 配置使用自己的 URL 语法，不能直接粘贴所有客户端的 Base64 VMess 分享链接。
本次构建不自动改变设备的路由、HEV 配置或启动服务。
