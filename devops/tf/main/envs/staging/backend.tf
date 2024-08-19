terraform {
  backend "s3" {
    bucket = "auto-validator-uwzlzz"
    key    = "staging/main.tfstate"
    region = "us-east-1"
  }
}
