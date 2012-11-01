package javro	
import java.util.ArrayList

class scala_arr[A](arr: ArrayList[Object]) extends Seq[A]{	
	var stored = arr;

	def apply(idx:Int):A ={
		return this.stored.get(idx).asInstanceOf[A]
	}

	def iterator():Iterator[A]={
		return new scala_iter[A](this.stored)
	}

	def length():Int = {
		return this.stored.size()
	}
}
