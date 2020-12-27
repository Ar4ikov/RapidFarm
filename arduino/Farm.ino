#include <OneWire.h>

int lamp = 1, fan = 2, nasos = 3;
OneWire ds(4);
char vlazh[3] = {A0, A1, A2}, photo = A3;
bool lampOn = false, fanOn = false, nasosOn = false;
unsigned int nasosLast = 0, lampLast = 0;
int nasosDelayOn = 10, lampDelayOn = 10, nasosDelayOff = 10, lampDelayOff = 10;
int tempMax = 30;
String data;

int lampPower(int x) // 1\0 - on\off
{
    if(x != lampOn)
    {
        lampOn = !lampOn;
        digitalWrite(lamp, lampOn);
    }
    
    lampLast = millis() / 60000;
    
    return 0;
}

int fanPower(int x) // 1\0 - on\off
{
    if(x != fanOn)
    {
        fanOn = !fanOn;
        digitalWrite(fan, fanOn);
    }
    
    return 0;
}

int nasosPower(int x) //1\0 - on\off
{
    if(x != nasosOn)
    {
        nasosOn = !nasosOn;
        digitalWrite(nasos, nasosOn);
    }
    
    nasosLast = millis() / 60000;
    
    return 0;
}

float tempData()
{
    byte temp[2];
    
    ds.reset();
    ds.write(0xCC);
    ds.write(0x44);
    
    delay(1000);
    
    ds.write(0xCC);
    ds.write(0xBE);
    
    temp[0] = ds.read();
    temp[1] = ds.read();
    
    float t =  ((data[1] << 8) | data[0]) * 0.0625;
    
    return t;
} 

int vlPochva(int x) // pin
{
    int value = analogRead(vlazh[x-1]);
    value = 1024 - value;
    value = value * 100 / 1024;
    
    return value;    
}

int photoData() //pin
{
    int value = analogRead(photo);
    value = 1024 - value;
    value = value * 100 / 1024;
    
    return value;
}

void setup()
{
    Serial.begin(9600);
    
    pinMode(lamp, OUTPUT);
    pinMode(fan, OUTPUT);
    pinMode(nasos, OUTPUT);
    
    for(int i=0; i<3; i++)
    {
        pinMode(vlazh[i], INPUT);
    }
    
    pinMode(photo, INPUT);    
}

void loop()
{
    if(nasosOn == true)
    {
        if(millis()/60000 - nasosLast >= nasosDelayOn) 
        { 
          nasosPower(0); 
        }
    }
    
    else if(nasosOn == false)
    {
        if(millis()/60000 - nasosLast >= nasosDelayOff) 
        { 
          nasosPower(1);
        }
    }
    
    if(lampOn == true)
    {
        if(millis()/60000 - lampLast >= lampDelayOn)
        {
            lampPower(0);
        }
    }
        
    else if(lampOn == false)
    {
        if(millis()/60000 - lampLast >= lampDelayOff)
        {
            lampPower(1);
        }
    } 
    
    if(tempData() >= tempMax)
    {
        fanPower(1);
    }
    
    else if(tempData < tempMax)
    {
        fanPower(0);
    }
    
    if(Serial.available())
    {
        data = Serial.readString();        
    }
    
    if(data[0] == 'I')
    {
        int dt_2 = data[2] - '0';
        
        if(data[1] == 'L')
        {
            Serial.println(lampPower(dt_2));
        }
        
        else if(data[1] == 'F')
        {
            Serial.println(fanPower(dt_2));
        }
        
        else if(data[1] == 'N')
        {
            Serial.println(nasosPower(dt_2));
        }

        else
        {
            Serial.println("Error");
        }
    }
    
    else if(data[0] == 'O')
    {
        
        int dt_2 = data[2] - 'O';
        
        if(data[1] == 'L')
        {
            Serial.println(lampOn);
        }
        
        else if(data[1] == 'F') 
        { 
            Serial.println(fanOn); 
        }
        
        else if(data[1] == 'N') 
        { 
            Serial.println(nasosOn); 
        }

        else if(data[1] == 'V')
        {
            Serial.println(vlPochva(dt_2 - 1));
        }
        
        else if(data[1] == 'P')
        {
            Serial.println(photoData());
        }

        else if(data[1] == 'T') 
        { 
            Serial.println(tempData()); 
        }
        
        else if(data[1] == 'A')
        {
            Serial.print("L: ");
            Serial.print(lampOn);
            Serial.print("; ");        
            
            Serial.print("F: ");
            Serial.print(fanOn);
            Serial.print("; ");
            
            Serial.print("N: ");
            Serial.print(nasosOn);
            Serial.print("; ");
            
            for(int i=0;i<3;i++)
            {
                Serial.print("V" + String(i+1) + ": ");
                Serial.print(vlPochva(data[i])+"; ");
            }

            Serial.print("P: ");
            Serial.print(photoData());
            Serial.print("; ");

            Serial.print("T: ");
            Serial.print(tempData());
            Serial.print("; ");
        }
            
        else
        {
            Serial.println("Error");
        }
    }

    else
    {
        Serial.println("Error");
    }
}
