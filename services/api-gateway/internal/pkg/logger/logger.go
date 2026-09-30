package logger

import (
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

var L *zap.Logger

func Init(env string) {
	var cfg zap.Config
	if env == "production" {
		cfg = zap.NewProductionConfig()
	} else {
		cfg = zap.NewDevelopmentConfig()
		cfg.EncoderConfig.EncodeLevel = zapcore.CapitalColorLevelEncoder
	}
	var err error
	L, err = cfg.Build()
	if err != nil {
		panic("failed to init logger: " + err.Error())
	}
	zap.ReplaceGlobals(L)
}

func Sync() {
	_ = L.Sync()
}
