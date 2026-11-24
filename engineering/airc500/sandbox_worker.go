// Offline fixture worker. The host admits one frozen case and no repository path.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"strings"
	"syscall"
)

func fail(err error) {
	if err != nil {
		panic(err)
	}
}

func contents(path string) []byte {
	data, err := os.ReadFile(path)
	fail(err)
	return data
}

func digest(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

func mountFlags(path string) map[string]bool {
	for _, line := range strings.Split(string(contents("/proc/self/mountinfo")), "\n") {
		fields := strings.Fields(line)
		if len(fields) > 5 && fields[4] == path {
			flags := make(map[string]bool)
			for _, value := range strings.Split(fields[5], ",") {
				flags[value] = true
			}
			return flags
		}
	}
	return nil
}

func onlyLoopback() bool {
	ifaces, err := net.Interfaces()
	fail(err)
	return len(ifaces) == 1 && ifaces[0].Flags&net.FlagLoopback != 0
}

func environmentAllowlisted() bool {
	for _, entry := range os.Environ() {
		name, _, _ := strings.Cut(entry, "=")
		switch name {
		case "PATH", "HOME", "HOSTNAME":
		default:
			return false
		}
	}
	return true
}

func absent(paths ...string) bool {
	for _, path := range paths {
		if _, err := os.Stat(path); !os.IsNotExist(err) {
			return false
		}
	}
	return true
}

func main() {
	if len(os.Args) != 1 {
		panic("worker accepts no commands")
	}
	packet := contents("/input/case.json")
	var fact struct{ ID, Field, Approved, Head string }
	fail(json.Unmarshal(packet, &fact))
	if fact.ID == "" || fact.Field == "" || fact.Approved == "" || fact.Head == "" {
		panic("incomplete fixture")
	}
	status := make(map[string]string)
	for _, line := range strings.Split(string(contents("/proc/self/status")), "\n") {
		key, value, ok := strings.Cut(line, ":")
		if ok {
			status[key] = strings.TrimSpace(value)
		}
	}
	inputs, err := os.ReadDir("/input")
	fail(err)
	ro, openErr := os.OpenFile("/input/case.json", os.O_WRONLY, 0)
	if openErr == nil {
		ro.Close()
	}
	file, err := os.CreateTemp("/scratch", "probe")
	fail(err)
	_, err = file.WriteString("synthetic")
	fail(err)
	fail(file.Close())
	fail(os.Remove(file.Name()))
	var scratch syscall.Statfs_t
	fail(syscall.Statfs("/scratch", &scratch))
	flags := mountFlags("/scratch")
	flagsZero := func(value string) bool { return value != "" && strings.Trim(value, "0") == "" }
	checks := map[string]bool{
		"nonroot": os.Getuid() == 65532 && os.Getgid() == 65532,
		"no_capabilities": flagsZero(status["CapEff"]) && flagsZero(status["CapBnd"]),
		"no_new_privileges": status["NoNewPrivs"] == "1",
		"seccomp": status["Seccomp"] == "2",
		"loopback_only": onlyLoopback(),
		"root_readonly": mountFlags("/")["ro"],
		"fixture_readonly": mountFlags("/input/case.json")["ro"] && openErr != nil,
		"only_one_input": len(inputs) == 1 && inputs[0].Name() == "case.json",
		"scratch_bounded": scratch.Type == 0x01021994 && scratch.Blocks > 0 && scratch.Blocks*uint64(scratch.Bsize) <= 4*1024*1024,
		"scratch_hardened": flags["rw"] && flags["noexec"] && flags["nodev"] && flags["nosuid"],
		"secrets_absent": absent("/input/host-secret-canary", "/.git", "/.env", "/run/secrets", "/run/docker.sock", "/var/run/docker.sock"),
		"environment_allowlisted": environmentAllowlisted(),
	}
	for name, ok := range checks {
		if !ok {
			fmt.Fprintln(os.Stderr, "failed containment check:", name)
			os.Exit(1)
		}
	}
	result := map[string]any{
		"checks": checks, "fixture_sha256": digest(packet), "worker_sha256": digest(contents("/worker")),
		"review": map[string]any{"id": fact.ID, "finding": fact.Approved != fact.Head, "approved": fact.Approved, "observed": fact.Head},
	}
	fail(json.NewEncoder(os.Stdout).Encode(result))
}
