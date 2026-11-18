package ali

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"net/http"
	"net/url"
	"strings"

	"github.com/QuantumNous/new-api/common"
	relaycommon "github.com/QuantumNous/new-api/relay/common"
	"github.com/gin-gonic/gin"
)

// Workspace keys are sealed against both the server secret and their official destination.
func (a *Adaptor) SignUpstreamRequest(_ *gin.Context, info *relaycommon.RelayInfo, method string, target *url.URL, header http.Header) error {
	encoded, sealed := strings.CutPrefix(info.ApiKey, "bailian-sealed-v1:")
	if !sealed {
		return nil
	}
	if target == nil || method != http.MethodPost || target.Scheme != "https" ||
		target.User != nil || !strings.HasSuffix(target.Host, ".maas.aliyuncs.com") ||
		target.Path != "/compatible-mode/v1/chat/completions" || info.ChannelSetting.Proxy != "" {
		return errors.New("unsupported sealed Bailian key destination")
	}
	key := sha256.Sum256([]byte("bailian-workspace-v1\x00" + common.CryptoSecret))
	block, err := aes.NewCipher(key[:])
	if err != nil {
		return err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return err
	}
	blob, err := base64.RawURLEncoding.DecodeString(encoded)
	if err != nil || len(blob) < gcm.NonceSize()+gcm.Overhead() {
		return errors.New("invalid sealed Bailian key")
	}
	secret, err := gcm.Open(nil, blob[:gcm.NonceSize()], blob[gcm.NonceSize():], []byte(target.Host))
	if err != nil {
		return errors.New("cannot open Bailian key for this workspace")
	}
	header.Set("Authorization", "Bearer "+string(secret))
	return nil
}
