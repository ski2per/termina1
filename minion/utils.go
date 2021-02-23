package minion

import (
	"net"
	"regexp"

	log "github.com/sirupsen/logrus"
)

func GetLocalAddr() (ipv4addr net.IP) {
	var ipv4Addr net.IP
	// Physical interface prefix on Linux
	re := regexp.MustCompile("^et|en")

	ifaces, err := net.Interfaces()
	if err != nil {
		log.Errorf("Error getting local interfaces: %+v\n", err.Error())
		return
	}
	for _, iface := range ifaces {
		if re.MatchString(iface.Name) {
			addrs, err := iface.Addrs()
			if err != nil {
				log.Errorf("Error getting interface address: %+v\n", err.Error())
				continue
			}

			for _, addr := range addrs {
				if ipv4Addr = addr.(*net.IPNet).IP.To4(); ipv4Addr != nil {
					// Break inner loop
					break
				}
			}
		}
		if ipv4Addr != nil {
			// Break outer loop after FIRST IPv4 address is found
			break
		}
	}
	return ipv4Addr
}
