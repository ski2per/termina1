package minion

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"net/http"
	"time"

	log "github.com/sirupsen/logrus"
)

type Minion struct {
	GruHost        string `env:"GRU_HOST" envDefault:"localhost"`
	GruSSHPort     int    `env:"GRU_SSH_PORT" envDefault:"22"`
	GruUsername    string `env:"GRU_USERNAME" envDefault:"gru"`
	GruPassword    string `env:"GRU_PASSWORD" envDefault:"P@ssw0rd"`
	GruAPIEndpoint string `env:"GRU_API_ENDPOINT" envDefault:"http://localhost:8000"`
	MinionHost     string `env:"MINION_HOST" envDefault:"localhost"`
	MinionSSHPort  int    `env:"MINION_SSH_PORT" envDefault:"22"`
	LogLevel       string `env:"GRU_LOG_LEVEL" envDefault:"debug"`
	MinionID       string `env:"MINION_ID"`
	MinionPublicIP string `env:"MINION_PUBLIC_IP"`
}

type randomPort struct {
	Port int `json:"port"`
}

type Meta struct {
	Name       string `json:"name"`
	Port       int    `json:"port"`
	InternalIP string `json:"ip"`
	PublicIP   string `json:"publicip"`
}

func (m *Minion) GetRandomPort() int {
	url := fmt.Sprintf("%s/port", m.GruAPIEndpoint)

	for {
		response, err := http.Get(url)
		if err == nil {
			responseData, err := ioutil.ReadAll(response.Body)
			if err == nil {
				random := randomPort{}
				json.Unmarshal(responseData, &random)
				return random.Port
			}
			log.Error("Error reading response data, retrying...")
			log.Error(responseData)
			time.Sleep(2 * time.Second)
			continue
		}
		log.Error("Error getting random port, retrying...")
		log.Error(err)
		time.Sleep(2 * time.Second)
	}
}

func (m *Minion) Register(meta Meta) error {
	log.Infof("Register minion with meta: %+v\n", meta)
	data, err := json.Marshal(meta)
	if err != nil {
		log.Error(err)
		return err
	}

	url := fmt.Sprintf("%s/register", m.GruAPIEndpoint)
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(data))
	if err != nil {
		log.Error(err)
		return err
	}

	if resp.StatusCode != 200 {
		log.Errorf("Register error, status code: %d\n", resp.StatusCode)
		return errors.New(fmt.Sprintf("Register error, status code: %d\n", resp.StatusCode))
	}
	return nil
}

func (m *Minion) Deregister(port int) {
	log.Infof("Deregister minion(port: %d)\n", port)
	client := &http.Client{}

	url := fmt.Sprintf("%s/deregister/%d", m.GruAPIEndpoint, port)

	req, err := http.NewRequest("DELETE", url, nil)
	if err != nil {
		fmt.Println(err)
		return
	}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Println(err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		log.Fatalf("Deregister error, status code: %d\n", resp.StatusCode)
	}
}
