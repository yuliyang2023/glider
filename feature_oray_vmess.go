//go:build oray_vmess || oray_vmess_tls

package main

import (
	_ "github.com/nadoo/glider/proxy/socks5"
	_ "github.com/nadoo/glider/proxy/vmess"
)
