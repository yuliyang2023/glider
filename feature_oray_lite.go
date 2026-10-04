//go:build oray_lite

package main

// Small proxy backend for HEV; leave routing and DHCP to OpenWrt/hev-manager.
import (
	_ "github.com/nadoo/glider/proxy/http"
	_ "github.com/nadoo/glider/proxy/mixed"
	_ "github.com/nadoo/glider/proxy/reject"
	_ "github.com/nadoo/glider/proxy/socks5"
	_ "github.com/nadoo/glider/proxy/ss"
	_ "github.com/nadoo/glider/proxy/tls"
	_ "github.com/nadoo/glider/proxy/trojan"
	_ "github.com/nadoo/glider/proxy/vless"
	_ "github.com/nadoo/glider/proxy/vmess"
	_ "github.com/nadoo/glider/proxy/ws"
)
