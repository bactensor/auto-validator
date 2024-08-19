terraform {
  backend "s3" {
    bucket = "auto-validator-uwzlzz"
    key    = "prod/main.tfstate"
    region = "us-east-1"
  }
}
