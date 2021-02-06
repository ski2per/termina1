package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"sync"
	"syscall"

	"github.com/caarlos0/env"
	log "github.com/sirupsen/logrus"
	"github.com/ski2per/gru/minion"
)

var m = minion.Minion{}

func init() {
	// Init configuration from evnironmental variables
	// cfg := config{}
	if err := env.Parse(&m); err != nil {
		fmt.Printf("%+v\n", err)
	}

	if len(m.MinionID) <= 0 {
		hostname, err := os.Hostname()
		if err != nil {
			log.Error("Error while getting hostname")
			log.Errorln(err)
		}
		m.MinionID = hostname
	}

	// Init Logrus, default to INFO
	log.SetFormatter(&log.TextFormatter{
		FullTimestamp:   true,
		TimestampFormat: "2006-01-02 15:04:05.00000",
	})
	logLvl, err := log.ParseLevel(m.LogLevel)
	if err != nil {
		logLvl = log.InfoLevel
	}
	log.SetLevel(logLvl)
}

func main() {
	fmt.Printf("\nMinion: %s\n\n", minion.Version)

	log.Debugf("%+v\n", m)
	log.Info("Trying to get random reversed port from Gru")
	randomPort := m.GetRandomPort()
	log.Infof("Got random reversed port: %d\n", randomPort)

	internalIP := minion.GetLocalAddr()
	meta := minion.Meta{
		Name:       m.MinionID,
		Port:       randomPort,
		InternalIP: internalIP.String(),
	}

	m.Register(meta)
	// Debug
	// os.Exit(0)

	remote := minion.Endpoint{
		Username: m.GruUsername,
		Password: m.GruPassword,
		Host:     m.GruHost,
		Port:     m.GruSSHPort,
	}

	local := minion.Endpoint{
		Host: m.MinionHost,
		Port: m.MinionSSHPort,
	}

	_, cancel := context.WithCancel(context.Background())

	// FIND NO WAY to exit blocked goroutine
	// wg := sync.WaitGroup{}
	// wg.Add(1)
	go func() {
		// minion.ConnectToGru(local, remote, cfg.GruReversePort)
		minion.ConnectToGru(local, remote, randomPort)
		// wg.Done()
	}()

	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM)

	cancel() // Signal cancellation to context.Context
	// wg.Wait() // Block here until are workers are done
	<-sigs // Blocks here until interrupted

	log.Info("Shutting down")
	// Make sure minion deregistered
	wg := sync.WaitGroup{}
	wg.Add(1)
	go func() {
		m.Deregister(randomPort)
		wg.Done()
	}()
	wg.Wait()
	log.Info("Bye Gru")
}
