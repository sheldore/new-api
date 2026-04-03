package service

import (
	"bytes"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/QuantumNous/new-api/common"
	"github.com/QuantumNous/new-api/model"
)

// NotifyDreamfacTopup 异步通知 dreamfac-admin 充值事件
// 失败不阻塞支付流程，仅记录日志
func NotifyDreamfacTopup(userId int, amount float64, tradeNo string) {
	webhookURL := os.Getenv("DREAMFAC_WEBHOOK_URL")
	apiSecret := os.Getenv("DREAMFAC_API_SECRET")
	if webhookURL == "" || apiSecret == "" {
		return
	}

	user, err := model.GetUserById(userId, false)
	if err != nil || user == nil || user.OidcId == "" {
		common.SysLog(fmt.Sprintf("dreamfac topup notify: user %d has no oidc_id, skip", userId))
		return
	}

	payload := fmt.Sprintf(`{"ssoUserId":"%s","amount":%.4f,"externalOrderId":"%s"}`,
		user.OidcId, amount, tradeNo)

	req, err := http.NewRequest(http.MethodPost, webhookURL, bytes.NewBufferString(payload))
	if err != nil {
		common.SysError(fmt.Sprintf("dreamfac topup notify: create request failed: %v", err))
		return
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiSecret)

	client := &http.Client{Timeout: 10 * time.Second}

	var lastErr error
	for attempt := 0; attempt < 3; attempt++ {
		resp, err := client.Do(req)
		if err != nil {
			lastErr = err
			time.Sleep(time.Duration(attempt+1) * time.Second)
			// 重建 request body（已被消费）
			req, _ = http.NewRequest(http.MethodPost, webhookURL, bytes.NewBufferString(payload))
			req.Header.Set("Content-Type", "application/json")
			req.Header.Set("Authorization", "Bearer "+apiSecret)
			continue
		}
		resp.Body.Close()
		if resp.StatusCode >= 200 && resp.StatusCode < 300 {
			common.SysLog(fmt.Sprintf("dreamfac topup notify: success for user %d, trade %s", userId, tradeNo))
			return
		}
		lastErr = fmt.Errorf("status %d", resp.StatusCode)
		time.Sleep(time.Duration(attempt+1) * time.Second)
		req, _ = http.NewRequest(http.MethodPost, webhookURL, bytes.NewBufferString(payload))
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Authorization", "Bearer "+apiSecret)
	}

	common.SysError(fmt.Sprintf("dreamfac topup notify: failed after 3 attempts for user %d, trade %s: %v", userId, tradeNo, lastErr))
}
