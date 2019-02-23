#define GBClock 8
#define GBIn 9
#define GBOut 10

#define bitDelay 60
#define byteDelay 240

uint8_t cmd;
uint8_t resp;

uint8_t GBSerialIO(uint8_t cmd) {
  uint8_t resp=0;
  for (uint8_t c=0;  c<8;  c++) {

    //write cycle
    
    if((cmd << c) & 0x80){
      digitalWrite(GBOut, 1);
    }
    else{ 
      digitalWrite(GBOut, 0);
    }
    digitalWrite(GBClock, 0);
    
    delayMicroseconds(bitDelay);

    //read cycle
    digitalWrite(GBClock, 1);
    resp <<= 1;
    if(digitalRead(GBIn))
    {
      resp |= 1;                  
    }
    delayMicroseconds(bitDelay);
  }
  delayMicroseconds(byteDelay);
  return resp;
}

void setup() {
  pinMode(GBIn, INPUT_PULLUP);
  pinMode(GBOut, OUTPUT);
  pinMode(GBClock, OUTPUT);
  digitalWrite(GBClock, 1);
  Serial.begin(9600);
}

void loop() {
  if (Serial.available() > 0) {
    cmd = Serial.read();
    resp = GBSerialIO(cmd);
    Serial.write(resp);
  }
}
