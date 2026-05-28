//! Single-producer single-consumer ring — heap only at construction.

use rtrb::RingBuffer;

use super::HotTick;

pub struct SpscIngress {
    consumer: rtrb::Consumer<HotTick>,
}

impl SpscIngress {
    pub fn new(capacity: usize) -> Result<Self, Box<dyn std::error::Error>> {
        let (_producer, consumer) = RingBuffer::<HotTick>::new(capacity);
        Ok(Self { consumer })
    }

    pub fn pop(&mut self) -> Result<HotTick, ()> {
        self.consumer.pop().map_err(|_| ())
    }
}
