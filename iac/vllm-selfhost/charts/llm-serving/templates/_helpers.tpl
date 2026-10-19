{{- define "llm.labels" -}}
app.kubernetes.io/part-of: llm-serving
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/* Runtime arguments for `vllm serve`. */}}
{{- define "llm.vllmArgs" -}}
- --served-model-name
- {{ .Values.model.servedName | quote }}
- --host
- 0.0.0.0
- --port
- "8000"
- --max-model-len
- {{ .Values.model.maxModelLen | quote }}
- --max-num-seqs
- {{ .Values.model.maxNumSeqs | quote }}
- --gpu-memory-utilization
- {{ .Values.model.gpuMemoryUtilization | quote }}
- --enable-prefix-caching
{{- if .Values.model.enforceEager }}
- --enforce-eager
{{- end }}
- --enable-auto-tool-choice
- --tool-call-parser
- {{ .Values.model.toolCallParser | quote }}
{{- if .Values.model.quantization }}
- --quantization
- {{ .Values.model.quantization | quote }}
{{- end }}
{{- if .Values.model.kvCacheDtype }}
- --kv-cache-dtype
- {{ .Values.model.kvCacheDtype | quote }}
{{- end }}
{{- if .Values.lmcache.enabled }}
- --kv-transfer-config
- '{"kv_connector":"LMCacheConnectorV1","kv_role":"kv_both"}'
{{- end }}
{{- if eq .Values.model.source "s3" }}
- --load-format
- runai_streamer
{{- end }}
{{- range .Values.model.extraArgs }}
- {{ . | quote }}
{{- end }}
{{- end -}}
