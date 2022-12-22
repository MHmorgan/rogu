package utils

import (
	"github.com/mhmorgan/rogu/sh"
	"strconv"
)

func UrlExists(url string) (responseCode int, ok bool, err error) {
	curl := "curl -sfIL -o /dev/null -w '%{http_code}' " + url
	b, code, err := sh.Exec(curl)
	if err != nil {
		return
	}
	responseCode, err = strconv.Atoi(b.String())
	ok = code == 0
	return
}
