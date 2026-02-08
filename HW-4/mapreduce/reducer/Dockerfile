FROM golang:1.23-alpine AS build

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY *.go ./

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /service

FROM alpine:latest

COPY --from=build /service /service

EXPOSE 8080

CMD ["/service"]