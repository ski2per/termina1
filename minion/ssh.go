package minion

import (
	"fmt"
	"io"
	"net"

	log "github.com/sirupsen/logrus"
	"golang.org/x/crypto/ssh"
)

type Endpoint struct {
	Host string
	Port int
}

func (endpoint *Endpoint) String() string {
	return fmt.Sprintf("%s:%d", endpoint.Host, endpoint.Port)
}

func ConnectToGru(minion *Minion, forwardPort int) error {
	// func ConnectToGru(minion Endpoint, gru Endpoint, forwardPort int) error {
	log.Info("Connecting to Gru")
	remote := Endpoint{
		// Username: minion.GruUsername,
		// Password: minion.GruPassword,
		Host: minion.GruHost,
		Port: minion.GruSSHPort,
	}

	local := Endpoint{
		Host: minion.MinionHost,
		Port: minion.MinionSSHPort,
	}

	remoteReverseEndpoint := Endpoint{
		Host: "localhost",
		Port: forwardPort,
	}

	sshConfig := &ssh.ClientConfig{
		// Remote(Gru) SSH username
		User: minion.GruUsername,
		Auth: []ssh.AuthMethod{
			ssh.Password(minion.GruPassword),
		},
		HostKeyCallback: ssh.InsecureIgnoreHostKey(),
	}

	// Connect to remote SSH server(Gru)
	remoteConn, err := ssh.Dial("tcp", remote.String(), sshConfig)
	if err != nil {
		// log.Fatalf("Dial into remote host error: %s", err)
		log.Errorf("Dial into remote host error: %s", err)
		minion.Deregister(forwardPort)
		return err
	}
	defer remoteConn.Close()

	// Listen SSH forwarding port on remote host
	reverseConn, err := remoteConn.Listen("tcp", remoteReverseEndpoint.String())
	if err != nil {
		log.Errorf("Listen forwaring port on remote host error: %s", err)
		return err
	}
	defer reverseConn.Close()

	// handle incoming connections on reverse forwarded tunnel
	for {
		log.Info("Setting up reverse SSH...")
		local, err := net.Dial("tcp", local.String())
		if err != nil {
			log.Errorf("Dial into local service error: %s", err)
		}

		// Block here to until reverse SSH connection on Gru
		reverse, err := reverseConn.Accept()
		if err != nil {
			log.Error("Lost connection to Gru")
			log.Error(err)
			return err
		}

		// Debug, optimize later
		go func() {
			handleForwarding(reverse, local)
			reverse.Close()
			local.Close()
		}()
	}
}

func handleForwarding(local net.Conn, remote net.Conn) {
	defer local.Close()
	chDone := make(chan bool)

	// remote -> local forwarding
	go func() {
		if _, err := io.Copy(local, remote); err != nil {
			log.Infof("Error while copying remote->local: %s", err)
		}
		chDone <- true
	}()

	// local -> remote forwarding
	go func() {
		if _, err := io.Copy(remote, local); err != nil {
			log.Infof("Error while copying local->remote: %s", err)
		}
		chDone <- true
	}()

	<-chDone
	log.Info("Connection closed(maybe by Gru)")
}
